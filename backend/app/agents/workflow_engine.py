import os
import json
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.services.retrieval_service import retrieval_service
from app.ai.prompt_builder import prompt_builder
from app.agents.execution_context import ExecutionContext
from app.agents.tool_registry import ToolRegistry
from app.agents.agent_registry import agent_registry

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
        """
        step_name = step.get("name", "Unnamed Step")
        agent_name = step.get("agent", "Review Agent")
        step_desc = step.get("description", "")
        
        context.record_step_start(step_name, agent_name)
        
        # Dynamically resolve agent class via registry
        try:
            agent = agent_registry.get_agent(agent_name)
        except Exception as e:
            err_msg = f"Failed to resolve agent '{agent_name}' in registry: {str(e)}"
            context.record_step_complete(step_name, "failed", err_msg)
            return "failed", {"error": err_msg}

        # 1. Retrieve RAG code context if repository is indexed
        code_context_str = ""
        if context.repository_id:
            # Query semantic chunks relevant to this specific step description
            retrieved_pairs = retrieval_service.retrieve_chunks(
                db=db,
                repository_id=context.repository_id,
                query=step_desc or context.goal,
                top_k=8
            )
            
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
            
            # Optimize and deduplicate chunks using existing prompt_builder helper
            optimized_chunks = prompt_builder.optimize_chunks(chunks_list)
            
            # Format chunks as text
            context_blocks = []
            for c in optimized_chunks:
                context_blocks.append(
                    f"--- File: {c['path']} (Lines {c['start_line']}-{c['end_line']}) ---\n"
                    f"{c['content']}\n"
                )
            code_context_str = "\n".join(context_blocks)

        # 2. Execute target Agent reasoning
        step_started = time.time()
        try:
            telemetry = {}
            if agent_name == "Summary Agent":
                # Summary Agent compiles findings using logs/history
                history_logs = "\n".join([
                    f"[{l.get('level', 'INFO')}] {l.get('message')}" 
                    for l in context.logs
                ])
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

                # Special Check: If Refactor Agent recommends code changes, flag for approval
                if agent_name == "Refactor Agent":
                    if res_dict.get("diff") or res_dict.get("proposed_code_blocks") or res_dict.get("refactorings"):
                        # Support both new schema keys and original backward compatible fields
                        context.diff = res_dict.get("diff") or ""
                        if not context.diff and res_dict.get("proposed_code_blocks"):
                            # construct unified diff if only proposed code blocks provided
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
                        
                        # Accumulate tokens used
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
            elapsed = time.time() - step_started
            context.agent_durations[agent_name] = context.agent_durations.get(agent_name, 0.0) + elapsed
            context.cache_misses += 1
            err_msg = f"Exception in {agent_name}: {str(e)}"
            context.add_log(err_msg, level="ERROR")
            context.record_step_complete(step_name, "failed", err_msg)
            return "failed", {"error": err_msg}
