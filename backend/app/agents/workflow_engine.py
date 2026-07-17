import os
import json
import time
import traceback
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.core.logger import logger
from app.models.repository import Repository
from app.services.retrieval_service import retrieval_service
from app.ai.prompt_builder import prompt_builder
from app.agents.execution_context import ExecutionContext
from app.agents.tool_registry import ToolRegistry
from app.agents.agent_registry import agent_registry


def _extract_agent_findings(
    agent_name: str,
    step: Dict[str, Any],
    res_dict: Dict[str, Any],
    context: ExecutionContext,
    telemetry: Dict[str, Any],
) -> None:
    """Store raw findings in shared_context_bundle for the collaboration pipeline."""
    if agent_name == "Summary Agent":
        return

    bundle = getattr(context, "shared_context_bundle", None)
    if bundle is None:
        context.shared_context_bundle = {}
        bundle = context.shared_context_bundle

    existing = bundle.get("agent_findings", [])
    step_id = step.get("step_id", "")
    confidence = res_dict.get("confidence", telemetry.get("confidence", 0.7))
    primary_file = bundle.get("primary_file", "")

    def append_finding(text: str, file_path: str = "", severity: str = "", symbol: str = "", line_range: str = ""):
        if not text or not str(text).strip():
            return
        existing.append({
            "agent": agent_name,
            "step_id": step_id,
            "text": str(text).strip(),
            "file_path": file_path or primary_file,
            "confidence": confidence,
            "severity": severity,
            "symbol": symbol,
            "line_range": line_range,
            "category": agent_name,
        })

    if res_dict.get("key_findings"):
        for f in res_dict["key_findings"]:
            append_finding(f)

    if res_dict.get("findings"):
        for f in res_dict["findings"]:
            append_finding(f)

    if res_dict.get("recommendations"):
        for f in res_dict["recommendations"]:
            append_finding(f, severity="medium")

    if res_dict.get("weaknesses"):
        for f in res_dict["weaknesses"]:
            append_finding(f, severity="high")

    if res_dict.get("vulnerabilities"):
        for v in res_dict["vulnerabilities"]:
            if isinstance(v, dict):
                append_finding(
                    v.get("description", str(v)),
                    file_path=v.get("file", primary_file),
                    severity=v.get("severity", "high").lower(),
                    line_range=str(v.get("line", "")),
                )
            else:
                append_finding(str(v), severity="high")

    bundle["agent_findings"] = existing


class WorkflowEngine:
    """
    Manages the sequential execution of planned agent steps, RAG lookup, and tools routing.
    Decoupled from concrete agents via dynamic registry lookup.
    """
    def __init__(self):
        # Instances are dynamically loaded and memoized in agent_registry
        pass

    async def execute_step(
        self,
        step: Dict[str, Any],
        context: ExecutionContext,
        tools: ToolRegistry,
        db: Session
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Executes a single step in the workflow.
        Returns a tuple of (status, telemetry_dict).
        Supports adaptive retrieval, shared context bundles, and throttled streaming.
        """
        step_name = step.get("name", "Unnamed Step")
        agent_name = step.get("agent", "Review Agent")
        step_desc = step.get("description", "")
        
        context.record_step_start(step_name, agent_name)
        
        try:
            agent = agent_registry.get_agent(agent_name)
        except Exception as e:
            err_msg = f"Failed to resolve agent '{agent_name}' in registry: {str(e)}"
            context.record_step_complete(step_name, "failed", err_msg)
            return "failed", {"error": err_msg}

        # 1. Retrieve RAG code context if repository is indexed
        code_context_str = ""
        if context.repository_id:
            # Query repo total_files once to determine adaptive top_k bounds
            repo = db.query(Repository).filter(Repository.id == context.repository_id).first()
            total_files = repo.total_files if repo else 100
            
            # Adaptive top_k selection: Small (6-8), Medium (10-15), Large (15-20)
            if total_files <= 50:
                top_k = 8
            elif total_files <= 250:
                top_k = 12
            else:
                top_k = 18
                
            # Retrieve more chunks only if average confidence is below 0.75
            if context.get_average_confidence() < 0.75:
                top_k += 5

            # --- Retrieve Planning Rules Configuration dynamically ---
            requires_graph = True
            requires_analysis = True
            try:
                from app.services.planning.planning_engine import planning_engine
                from app.services.planning.planning_rules import PLANNING_RULES
                intent = planning_engine.detect_intent(context.goal)
                rule = PLANNING_RULES.get(intent, PLANNING_RULES["General Analysis"])
                requires_graph = rule.get("requires_graph_context", True)
                requires_analysis = rule.get("requires_repository_analysis", True)
            except Exception:
                pass

            # --- Graph-first candidate file selection ---
            graph_candidate_paths: List[str] = []
            if requires_graph:
                try:
                    from app.services.knowledge_graph import graph_manager as _gm
                    import time
                    if _gm.exists(context.repository_id):
                        context.graph_cache_hit = context.repository_id in _gm._cache
                        stats = _gm.get_statistics(context.repository_id)
                        context.graph_nodes = stats.get("total_nodes", 0)
                        context.graph_edges = stats.get("total_edges", 0)
                        context.graph_build_time = stats.get("build_time_ms", 0)

                        start_trav = time.time()
                        graph_candidate_paths = _gm.candidate_files_for_goal(
                            context.repository_id,
                            step_desc or context.goal,
                            max_files=30,
                        )
                        dt_trav = (time.time() - start_trav) * 1000  # ms

                        context.graph_candidates_selected = len(graph_candidate_paths)
                        context.graph_traversal_time = dt_trav

                        if graph_candidate_paths:
                            logger.info(
                                f"[WorkflowEngine] Graph selected {len(graph_candidate_paths)} candidate files "
                                f"for step '{step_name}'"
                            )
                except Exception as _ge:
                    logger.debug(f"[WorkflowEngine] Graph candidate selection skipped: {_ge}")

            # --- Repository Analysis Engine Query ---
            if requires_analysis:
                try:
                    from app.services.repository_analysis.analysis_engine import repository_analysis_engine
                    from app.services.knowledge_graph import graph_manager as _gm

                    if _gm.exists(context.repository_id):
                        keywords = [w.lower() for w in (step_desc or context.goal).split() if len(w) > 3]
                        related_symbols = []
                        for kw in keywords[:5]:
                            related_symbols.extend(_gm.search(context.repository_id, kw))
                        related_symbol_ids = [s["id"] for s in related_symbols if s.get("type") == "symbol"]

                        impacted_files = []
                        for sym_id in related_symbol_ids[:3]:
                            impacted_files.extend(repository_analysis_engine.impacted_files(context.repository_id, sym_id))

                        hotspots = repository_analysis_engine.detect_architecture_hotspots(context.repository_id).hotspots
                        circulars = repository_analysis_engine.detect_circular_dependencies(context.repository_id)

                        analysis_context_data = {
                            "impacted_files": list(set(impacted_files))[:10],
                            "related_symbols": related_symbol_ids[:10],
                            "hotspots": [h["file"] for h in hotspots[:5] if h.get("file")],
                            "circular_paths": [c.cycle for c in circulars[:3]]
                        }

                        bundle = getattr(context, "shared_context_bundle", None)
                        if bundle is not None:
                            bundle["analysis"] = analysis_context_data
                        else:
                            context.shared_context_bundle = {"analysis": analysis_context_data}
                except Exception as _ae:
                    logger.debug(f"[WorkflowEngine] Repository analysis query failed/skipped: {_ae}")
            
            # Check if SharedContextBundle exists on context to avoid duplicate FAISS/DB queries
            bundle = getattr(context, "shared_context_bundle", None)
            if bundle is not None:
                # Sort/filter chunks locally using simple keyword similarity against step_desc
                words = [w.lower() for w in (step_desc or context.goal).split() if len(w) > 3]
                scored = []
                all_chunks = bundle.get("relevant_chunks", [])
                for chunk, score in all_chunks:
                    # Apply graph candidate filter when available (with fallback)
                    if graph_candidate_paths and chunk.path not in graph_candidate_paths:
                        continue
                    match_score = score
                    content_lower = chunk.content.lower()
                    path_lower = chunk.path.lower()
                    for w in words:
                        if w in content_lower:
                            match_score += 0.1
                        if w in path_lower:
                            match_score += 0.2
                    scored.append((chunk, match_score))

                # Fallback: if graph filtering produced 0 results, use all chunks
                if not scored and graph_candidate_paths:
                    logger.debug(f"[WorkflowEngine] Graph filter empty — falling back to full bundle")
                    for chunk, score in all_chunks:
                        words_score = score
                        content_lower = chunk.content.lower()
                        path_lower = chunk.path.lower()
                        for w in words:
                            if w in content_lower:
                                words_score += 0.1
                            if w in path_lower:
                                words_score += 0.2
                        scored.append((chunk, words_score))
                
                scored.sort(key=lambda x: x[1], reverse=True)
                retrieved_pairs = scored[:top_k]
            else:
                retrieved_pairs = retrieval_service.retrieve_chunks(
                    db=db,
                    repository_id=context.repository_id,
                    query=step_desc or context.goal,
                    top_k=top_k,
                    workflow_type=context.workflow_type
                )
                # If graph candidates exist, re-rank by prioritising graph files
                if graph_candidate_paths and retrieved_pairs:
                    boosted = []
                    rest = []
                    for chunk, score in retrieved_pairs:
                        if chunk.path in graph_candidate_paths:
                            boosted.append((chunk, score + 0.25))
                        else:
                            rest.append((chunk, score))
                    retrieved_pairs = sorted(boosted + rest, key=lambda x: x[1], reverse=True)[:top_k]
            
            chunks_list = []
            for chunk, score in retrieved_pairs:
                context.add_chunk(chunk.path, chunk.start_line, chunk.end_line, score)
                chunks_list.append({
                    "id": chunk.id,
                    "path": chunk.path,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "content": chunk.content,
                    "score": score
                })
            
            # Optimize and deduplicate chunks (uses query for context compression)
            optimized_chunks = prompt_builder.optimize_chunks(chunks_list, query=step_desc or context.goal)
            
            context_blocks = []
            for c in optimized_chunks:
                context_blocks.append(
                    f"--- File: {c['path']} (Lines {c['start_line']}-{c['end_line']}) ---\n"
                    f"{c['content']}\n"
                )
            code_context_str = "\n".join(context_blocks)

        # 2. Bind dynamic throttled streaming callback to agent
        from app.services.workflow_manager import workflow_manager
        
        def on_chunk_cb(text: str):
            # Immediately publish to SSE listeners
            workflow_manager.publish_event(
                workflow_id=context.workflow_id,
                event_type="workflow_log",
                data=text
            )
            
        agent.on_chunk = on_chunk_cb
        step_started = time.time()
        
        try:
            telemetry = {}
            if agent_name == "Summary Agent":
                # Summary Agent compiles findings using logs/history
                validated_prefix = context.collaboration_context.get("validated_findings_text", "")
                history_logs = "\n".join([
                    f"[{l.get('level', 'INFO')}] {l.get('message')}"
                    for l in context.logs
                ])
                if validated_prefix:
                    history_logs = validated_prefix + "\n\n" + history_logs
                res_model, telemetry = await agent.analyze_history(
                    goal=context.goal,
                    execution_context_logs=history_logs
                )
                res_dict = res_model.model_dump()
                context.add_summary(res_dict.get("executive_summary", ""))
                context.record_agent_output(agent_name, res_dict, res_model.confidence)
            else:
                # Other agents evaluate active step based on retrieved context
                res_model, telemetry = await agent.analyze_step(
                    goal=context.goal,
                    step_description=step_desc,
                    code_context=code_context_str
                )
                res_dict = res_model.model_dump()
                context.record_agent_output(agent_name, res_dict, res_model.confidence)
                _extract_agent_findings(agent_name, step, res_dict, context, telemetry)

                # Special Check: If Refactor Agent recommends code changes, flag for approval
                if agent_name == "Refactor Agent":
                    if res_dict.get("diff") or res_dict.get("proposed_code_blocks") or res_dict.get("refactorings"):
                        context.diff = res_dict.get("diff") or ""
                        if not context.diff and res_dict.get("proposed_code_blocks"):
                            blocks = []
                            for idx, b in enumerate(res_dict["proposed_code_blocks"]):
                                blocks.append(
                                    f"--- {b.get('file')}\n+++ {b.get('file')} (Refactored)\n"
                                    f"@@ -1,1 +1,1 @@\n"
                                    f"- {b.get('original_code')}\n+ {b.get('new_code')}\n"
                                )
                            context.diff = "\n".join(blocks)
                        
                        mod_files = res_dict.get("files_to_modify") or []
                        if not mod_files and res_dict.get("proposed_code_blocks"):
                            mod_files = [b.get("file") for b in res_dict["proposed_code_blocks"] if b.get("file")]
                        context.affected_files = list(set(mod_files))
                        
                        context.approval_reason = res_dict.get("refactoring_rationale") or "Refactoring suggestions"
                        context.approval_status = "pending"
                        
                        context.add_log("Refactor Agent generated code modifications. Halting for Human Approval.")
                        context.record_step_complete(step_name, "pending_approval", "Code edits proposed. Requires developer verification.")
                        
                        context.tokens_used += telemetry.get("total_tokens", 0)
                        if telemetry.get("provider"):
                            context.providers_used.append(telemetry["provider"])
                        
                        elapsed = time.time() - step_started
                        context.agent_durations[agent_name] = context.agent_durations.get(agent_name, 0.0) + elapsed
                        if telemetry.get("cached"):
                            context.cache_hits += 1
                        else:
                            context.cache_misses += 1
                        context.retry_count += telemetry.get("retry_count", 0)
                            
                        return "pending_approval", telemetry

            # Mark step complete
            context.record_step_complete(step_name, "completed", f"Analyzed via {agent_name}")
            context.tokens_used += telemetry.get("total_tokens", 0)
            if telemetry.get("provider"):
                context.providers_used.append(telemetry["provider"])
                
            elapsed = time.time() - step_started
            context.agent_durations[agent_name] = context.agent_durations.get(agent_name, 0.0) + elapsed
            if telemetry.get("cached"):
                context.cache_hits += 1
            else:
                context.cache_misses += 1
            context.retry_count += telemetry.get("retry_count", 0)

            return "completed", telemetry

        except Exception as e:
            tb = traceback.format_exc()
            elapsed = time.time() - step_started
            context.agent_durations[agent_name] = context.agent_durations.get(agent_name, 0.0) + elapsed
            context.cache_misses += 1
            err_msg = f"{type(e).__name__} in {agent_name}: {e}"
            logger.exception(
                f"[WorkflowEngine] Step '{step_name}' failed — {err_msg}\n{tb}"
            )
            context.add_log(err_msg, level="ERROR")
            context.add_log(f"Traceback:\n{tb}", level="ERROR")
            context.record_step_complete(step_name, "failed", err_msg)
            return "failed", {"error": err_msg}
            
        finally:
            # Safely cleanup dynamic stream callback attribute
            if hasattr(agent, "on_chunk"):
                delattr(agent, "on_chunk")
