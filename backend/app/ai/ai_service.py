import time
import uuid
import random
import asyncio
import httpx
from typing import List, Dict, Any, Type, Optional, Tuple
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logger import logger
from app.models.repository import Repository
from app.services.retrieval_service import retrieval_service
from app.ai.provider_factory import provider_factory
from app.ai.token_manager import token_manager
from app.ai.prompt_builder import prompt_builder
from app.ai.response_parser import response_parser, AIResponseParsingError
from app.ai.cache import ai_cache
from app.ai.schemas import (
    ReviewSchema,
    ExplainSchema,
    TestsSchema,
    BugsSchema,
    AIMetadata,
    TraceabilityRef,
    BaseAISchema
)

class AIService:
    """
    Orchestrates the AI reasoning pipeline. Manages semantic context, caching, provider failover, 
    and output validation.
    """
    def __init__(self):
        self._task_queries = {
            "review": (
                "overall codebase architecture patterns, structural design strengths, improvements, "
                "security observations, performance, and general recommendations"
            ),
            "explain": (
                "code entry points, system architecture, component relationships, module roles, "
                "execution flow, and request or data flow pipelines"
            ),
            "tests": (
                "unit testing suggestions, integration test flows, mock opportunities, and edge cases"
            ),
            "bugs": (
                "logical issues, risk areas, bare excepts, resource leaks, async concerns, null validations, "
                "and security issues"
            )
        }
        
        self._schema_mappings: Dict[str, Type[BaseAISchema]] = {
            "review": ReviewSchema,
            "explain": ExplainSchema,
            "tests": TestsSchema,
            "bugs": BugsSchema
        }

    def _get_prompt_version(self, task_type: str) -> str:
        """
        Resolves prompt version depending on target task.
        """
        if task_type == "review":
            return settings.PROMPT_VERSION_REVIEW
        elif task_type == "explain":
            return settings.PROMPT_VERSION_EXPLAIN
        elif task_type == "tests":
            return settings.PROMPT_VERSION_TESTS
        return settings.PROMPT_VERSION_BUGS

    def _get_provider_details(self, provider_name: str) -> Tuple[str, str]:
        """
        Resolves the configured model name and API key for a target provider.
        """
        key = provider_name.strip().lower()
        if key == "google":
            return settings.GOOGLE_MODEL_NAME, settings.GOOGLE_API_KEY
        elif key == "groq":
            return settings.GROQ_MODEL_NAME, settings.GROQ_API_KEY
        elif key == "openrouter":
            return settings.OPENROUTER_MODEL_NAME, settings.OPENROUTER_API_KEY
        elif key == "nvidia":
            return settings.NVIDIA_MODEL_NAME, settings.NVIDIA_API_KEY
        else:
            raise ValueError(f"Unsupported AI provider: {provider_name}")

    async def analyze_repository(
        self,
        db: Session,
        repository_id: str,
        task_type: str,
        repository_metadata: Any
    ) -> BaseAISchema:
        """
        Coordinates semantic context retrieval, caching, multi-provider failover chains, 
        Pydantic response validation, and metadata auditing.
        """
        task_key = task_type.strip().lower()
        if task_key not in self._schema_mappings:
            raise ValueError(f"Unsupported task type for AI evaluation: '{task_type}'")
            
        schema_cls = self._schema_mappings[task_key]
        started_timestamp = time.time()
        request_id = f"ai_req_{uuid.uuid4().hex[:12]}"
        
        # 1. Retrieve Repository Hash for Caching
        repo = db.query(Repository).filter(Repository.id == repository_id).first()
        repository_hash = repo.repository_hash if (repo and repo.repository_hash) else repository_id

        # 2. Query Semantic retrieval (AI Reasoning NEVER bypasses RetrievalService)
        query = self._task_queries.get(task_key, "codebase structure")
        logger.info(f"AIService: Performing semantic search query for '{task_key}' on repo {repository_id}")
        retrieved_pairs = retrieval_service.retrieve_chunks(
            db=db,
            repository_id=repository_id,
            query=query,
            top_k=settings.RETRIEVAL_LIMIT
        )

        # Convert to dictionary representation for preprocessing
        chunks_list = []
        for chunk, score in retrieved_pairs:
            chunks_list.append({
                "id": chunk.id,
                "path": chunk.path,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "content": chunk.content,
                "score": score
            })

        # 3. Optimize context: Deduplicate and Merge overlapping/contiguous file ranges
        optimized_chunks = prompt_builder.optimize_chunks(chunks_list)

        # 4. Perform Token Budgeting
        metadata_dict = {
            "repository_name": repository_metadata.repository_name,
            "primary_language": repository_metadata.primary_language,
            "framework": repository_metadata.framework,
            "total_files": repository_metadata.total_files,
            "directories": repository_metadata.directories,
            "package_managers": repository_metadata.package_managers,
            "dependencies": repository_metadata.dependencies,
            "entrypoints": [f.path for f in repository_metadata.largest_files[:3]]
        }

        # Retrieve and build Graph Context block if available
        graph_ctx = ""
        try:
            from app.services.knowledge_graph import graph_manager
            if graph_manager.exists(repository_id):
                graph_ctx = graph_manager.build_graph_context(repository_id, query)
        except Exception as _ge:
            logger.debug(f"AIService: Failed to build graph context: {_ge}")

        # Retrieve and build Repository Analysis context block if available
        analysis_ctx = ""
        try:
            from app.services.repository_analysis.analysis_storage import analysis_storage
            from app.db.session import SessionLocal
            
            with SessionLocal() as db:
                repo_row = db.query(Repository).filter(Repository.id == repository_id).first()
                intel_path = repo_row.intelligence_path if repo_row else None
            
            if intel_path and analysis_storage.is_valid_cache(intel_path, None):
                summary_data = analysis_storage.load_summary(intel_path)
                dead_code_data = analysis_storage.load_dead_code(intel_path) or {}
                hotspots_data = analysis_storage.load_hotspots(intel_path) or {}
                architecture_data = analysis_storage.load_architecture(intel_path) or {}
                
                lines = ["[Repository Analysis]"]
                if summary_data:
                    lines.append(f"Health Score: {summary_data.get('health_score')}%")
                
                issues = architecture_data.get("issues", [])
                if issues:
                    lines.append("\nArchitecture Issues:")
                    for issue in issues[:3]:
                        lines.append(f"- [{issue.get('severity').upper()}] {issue.get('message')}")
                        
                unused = dead_code_data.get("unused_symbols", [])
                if unused:
                    lines.append("\nUnused Symbols (Potential Dead Code):")
                    for sym in unused[:5]:
                        lines.append(f"- {sym.get('name')} in {sym.get('file')}")
                        
                hotspots = hotspots_data.get("hotspots", [])
                if hotspots:
                    lines.append("\nHigh Coupling Hotspots:")
                    for hs in hotspots[:3]:
                        lines.append(f"- {hs.get('name')} ({hs.get('type')}) degree: {hs.get('coupling_degree')}")
                        
                analysis_ctx = "\n".join(lines)
        except Exception as _ae:
            logger.debug(f"AIService: Failed to build analysis context: {_ae}")

        # Render empty chunks prompt to count base prompt overhead tokens
        base_sys_p, base_usr_p = prompt_builder.build_prompts(task_key, metadata_dict, [], graph_context=graph_ctx, analysis_context=analysis_ctx)
        base_tokens = token_manager.estimate_tokens(base_sys_p) + token_manager.estimate_tokens(base_usr_p)
        
        # Select and truncate chunks to fit configured MAX_TOKENS limit
        budgeted_chunks, budgeted_tokens = token_manager.budget_chunks(
            optimized_chunks,
            base_prompt_tokens=base_tokens,
            max_budget=settings.MAX_TOKENS
        )

        # 5. Caching Validation
        retrieval_hash = ai_cache.compute_retrieval_hash(budgeted_chunks)
        prompt_version = self._get_prompt_version(task_key)
        active_provider = settings.AI_PROVIDER
        active_model, _ = self._get_provider_details(active_provider)

        cache_key = ai_cache.generate_cache_key(
            repository_hash=repository_hash,
            retrieval_hash=retrieval_hash,
            task_type=task_key,
            provider=active_provider,
            selected_model=active_model,
            prompt_version=prompt_version,
            retrieval_limit=settings.RETRIEVAL_LIMIT,
            temperature=settings.TEMPERATURE
        )

        cached_json = ai_cache.get(cache_key)
        if cached_json:
            # Successfully loaded cached result
            try:
                # Update metadata for cache tracing
                if "ai_metadata" in cached_json and cached_json["ai_metadata"]:
                    cached_json["ai_metadata"]["cache_hit"] = True
                    cached_json["ai_metadata"]["completed_timestamp"] = time.time()
                    cached_json["ai_metadata"]["latency"] = time.time() - started_timestamp
                
                response_model = schema_cls.model_validate(cached_json)
                
                # Trace logs only (Never log code or responses)
                logger.info(
                    f"AIService: Operation completed via Cache Hit. Request ID: {request_id}. "
                    f"Provider: {active_provider}. Model: {active_model}."
                )
                return response_model
            except Exception as parse_err:
                logger.warning(f"AIService: Failed to validate cached JSON schema: {parse_err}. Re-analyzing.")

        # 6. Resolve Prompt Messages
        system_prompt, user_prompt = prompt_builder.build_prompts(task_key, metadata_dict, budgeted_chunks, graph_context=graph_ctx, analysis_context=analysis_ctx)

        # 7. Multi-Provider Failover Loop & Retries
        provider_chain = [p.strip().lower() for p in settings.AI_PROVIDER_CHAIN.split(",")]
        
        # Ensure active configured provider is prioritised at index 0
        if active_provider.lower() not in provider_chain:
            provider_chain.insert(0, active_provider.lower())
        else:
            provider_chain.remove(active_provider.lower())
            provider_chain.insert(0, active_provider.lower())

        final_response_obj: Optional[BaseAISchema] = None
        provider_used_after_failover = None
        last_exception = None

        for current_provider in provider_chain:
            # Resolve provider parameters
            try:
                model_name, api_key = self._get_provider_details(current_provider)
            except ValueError as val_err:
                # Unknown provider name — silently skip (configuration issue, not a runtime failure)
                logger.info(f"AIService: Skipping unknown provider in chain: {val_err}")
                continue

            if not api_key or "api_key_here" in api_key:
                # Provider not configured — skip silently (not a failure, just not set up)
                logger.info(f"AIService: Provider '{current_provider}' has no API key configured. Skipping.")
                continue

            provider_used_after_failover = current_provider if current_provider != active_provider else None
            logger.info(f"AIService: Requesting LLM response from provider '{current_provider}' / model '{model_name}'")
            
            client = provider_factory.get_client(current_provider)
            
            # Retry loop for this provider
            retry_count = 0
            for attempt in range(settings.MAX_RETRIES):
                retry_count = attempt
                try:
                    # Invoke model client
                    response = await client.generate(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        model_name=model_name,
                        api_key=api_key,
                        temperature=settings.TEMPERATURE,
                        max_tokens=settings.MAX_TOKENS,
                        timeout=settings.TIMEOUT
                    )
                    
                    # Parse, clean and validate response
                    parsed_model = response_parser.parse_and_validate(response.text, schema_cls)
                    
                    # Successfully parsed and validated!
                    completed_timestamp = time.time()
                    latency = completed_timestamp - started_timestamp
                    
                    # Map Traceability Reference list
                    traceability_refs = [
                        TraceabilityRef(
                            path=c["path"],
                            start_line=c["start_line"],
                            end_line=c["end_line"],
                            chunk_id=c["id"],
                            score=c.get("score")
                        ) for c in budgeted_chunks
                    ]

                    # Populate Metadata
                    metadata = AIMetadata(
                        provider=active_provider,
                        provider_used_after_failover=provider_used_after_failover,
                        model=model_name,
                        latency=latency,
                        prompt_tokens=response.prompt_tokens or token_manager.estimate_tokens(system_prompt + user_prompt),
                        completion_tokens=response.completion_tokens or token_manager.estimate_tokens(response.text),
                        total_tokens=response.total_tokens or (response.prompt_tokens + response.completion_tokens),
                        retry_count=retry_count,
                        cache_hit=False,
                        fallback_flag=False,
                        request_id=request_id,
                        started_timestamp=started_timestamp,
                        completed_timestamp=completed_timestamp,
                        estimated_cost=0.0
                    )

                    parsed_model.traceability_refs = traceability_refs
                    parsed_model.is_fallback = False
                    parsed_model.ai_metadata = metadata
                    
                    final_response_obj = parsed_model
                    
                    # Save results to Cache
                    ai_cache.set(cache_key, final_response_obj.model_dump())
                    break

                except Exception as err:
                    last_exception = err
                    # Only warn on actual network / API failures (provider was attempted)
                    logger.warning(
                        f"AIService: Provider '{current_provider}' attempt {attempt + 1}/{settings.MAX_RETRIES} failed: {type(err).__name__}: {err}"
                    )
                    
                    # Exponential backoff with jitter before retry
                    if attempt < settings.MAX_RETRIES - 1:
                        sleep_time = (2 ** attempt) + random.uniform(0.1, 0.5)
                        await asyncio.sleep(sleep_time)

            if final_response_obj:
                # Successfully received response — exit provider chain loop
                break
            else:
                logger.error(
                    f"AIService: All {settings.MAX_RETRIES} retries exhausted for provider '{current_provider}'. "
                    f"Trying next provider in chain."
                )

        if final_response_obj:
            # Log successful operation details only (Never log code or responses)
            logger.info(
                f"AIService: Analysis successful. Request ID: {request_id}. "
                f"Used Provider: {provider_used_after_failover or active_provider}. Model: {final_response_obj.ai_metadata.model}. "
                f"Latency: {final_response_obj.ai_metadata.latency:.3f}s. Tokens: {final_response_obj.ai_metadata.total_tokens}."
            )
            return final_response_obj

        # 8. Every configured provider in the chain was attempted and failed
        # Only reached here when ALL providers with valid API keys have exhausted all retries.
        logger.error(
            f"AIService: All providers in the failover chain failed for request {request_id}. "
            f"Activating heuristic fallback. Last error: {last_exception}"
        )

        # Safely resolve attributes from repository_metadata to support Mock/arbitrary metadata objects
        docker_support = getattr(repository_metadata, 'docker_support', False)
        github_actions = getattr(repository_metadata, 'github_actions', False)
        cicd = getattr(repository_metadata, 'cicd', False)
        tests_present = getattr(repository_metadata, 'tests_present', False)
        readme_present = getattr(repository_metadata, 'readme_present', False)
        license_val = getattr(repository_metadata, 'license', None)
        dependencies = getattr(repository_metadata, 'dependencies', {}) or {}
        largest_files = getattr(repository_metadata, 'largest_files', []) or []
        primary_lang = getattr(repository_metadata, 'primary_language', 'Unknown')
        framework = getattr(repository_metadata, 'framework', 'None')

        # Helper functions to extract properties from list items (handles dicts, models, mocks)
        def get_item_path(item) -> str:
            if not item: return ""
            return item.get("path") if isinstance(item, dict) else getattr(item, "path", "")

        def get_item_size(item) -> int:
            if not item: return 0
            return item.get("size", 0) if isinstance(item, dict) else getattr(item, "size", 0)

        fallback_json = {}
        if task_key == "review":
            strengths = []
            if docker_support:
                strengths.append("Docker support is configured (Dockerfile present).")
            if github_actions:
                strengths.append("CI/CD workflow is integrated via GitHub Actions.")
            if cicd:
                strengths.append("Other CI/CD configurations are defined in the repository.")
            if tests_present:
                strengths.append("Test suite folder/file structure is present.")
            if not strengths:
                strengths = ["Information could not be determined from the available repository context."]

            improvements = []
            if not tests_present:
                improvements.append("Missing unit test coverage structures.")
            if not readme_present:
                improvements.append("Missing README documentation at the repository root.")
            if not license_val or license_val == "None":
                improvements.append("No open source LICENSE file was detected.")
            if not improvements:
                improvements = ["Information could not be determined from the available repository context."]

            security_obs = []
            if docker_support:
                security_obs.append("Dockerfile and environment configs were parsed. Verify environment credentials security.")
            if dependencies:
                security_obs.append("Core dependencies mapped for security scanning.")
            if not security_obs:
                security_obs = ["Information could not be determined from the available repository context."]

            performance_obs = []
            if largest_files:
                largest_path = get_item_path(largest_files[0])
                largest_size = get_item_size(largest_files[0])
                performance_obs.append(f"Large code files detected (largest is `{largest_path}` at {largest_size} bytes).")
            if not performance_obs:
                performance_obs = ["Information could not be determined from the available repository context."]

            maintainability_obs = []
            if primary_lang and primary_lang != "Unknown":
                maintainability_obs.append(f"Main language determined: `{primary_lang}`.")
            if framework and framework != "None":
                maintainability_obs.append(f"Framework structure: `{framework}`.")
            if not maintainability_obs:
                maintainability_obs = ["Information could not be determined from the available repository context."]

            recs = []
            if not tests_present:
                recs.append("Recommendation: Establish automated test coverage by adding test suites.")
            if largest_files:
                recs.append("Recommendation: Consider modularizing larger files to optimize code structure.")
            if not recs:
                recs = ["Information could not be determined from the available repository context."]

            fallback_json = {
                "executive_summary": "Structured repository assessment generated from repository metadata, scanner outputs, dependency analysis, and retrieved repository context.",
                "strengths": strengths,
                "improvements": improvements,
                "security_observations": security_obs,
                "performance_observations": performance_obs,
                "maintainability_observations": maintainability_obs,
                "recommendations": recs
            }

        elif task_key == "bugs":
            error_prone = []
            null_concerns = []
            async_concerns = []
            resource_obs = []
            for chunk in chunks_list:
                content = chunk.get("content", "")
                path = chunk.get("path", "")
                start = chunk.get("start_line", 1)
                if "except:" in content or "except Exception:" in content:
                    if "pass" in content or "continue" in content:
                        error_prone.append(f"Silent exception handling (bare except block with `pass` or `continue`) in `{path}` near line {start}.")
                if "open(" in content and "with " not in content:
                    resource_obs.append(f"Resource acquisition without context manager (`open()` called outside `with`) in `{path}` near line {start}.")
                if "async " in content and "await " not in content and ".ts" in path:
                    async_concerns.append(f"Async function definition without explicit `await` expression in `{path}` near line {start}.")
                if " == null" in content or " != null" in content:
                    null_concerns.append(f"Explicit null validation checks in `{path}` near line {start}; verify safety of property dereferencing.")

            perf_concerns = []
            if largest_files:
                largest_path = get_item_path(largest_files[0])
                largest_size = get_item_size(largest_files[0])
                if largest_size > 10000:
                    perf_concerns.append(f"Large source file `{largest_path}` ({largest_size} bytes) may degrade parsing and memory usage.")

            fallback_json = {
                "logical_issues": ["No significant issues detected."],
                "risk_areas": ["No significant issues detected."],
                "error_prone_patterns": error_prone or ["No significant issues detected."],
                "null_handling_concerns": null_concerns or ["No significant issues detected."],
                "async_concerns": async_concerns or ["No significant issues detected."],
                "resource_management_observations": resource_obs or ["No significant issues detected."],
                "security_observations": ["No significant issues detected."],
                "performance_concerns": perf_concerns or ["No significant issues detected."]
            }

        elif task_key == "tests":
            unit_recs = []
            for f in largest_files[:2]:
                f_path = get_item_path(f)
                unit_recs.append(f"Write unit tests covering logical blocks of `{f_path}`.")

            integration_recs = []
            if framework == "FastAPI":
                integration_recs.append("Use `fastapi.testclient.TestClient` to perform request/response integration checks on routes.")
            elif framework == "Express":
                integration_recs.append("Use `supertest` to verify HTTP endpoint status codes and JSON payloads.")
            elif framework and framework != "None":
                integration_recs.append(f"Set up API client integration suites matching the `{framework}` configuration.")
            else:
                integration_recs.append("Information could not be determined from the available repository context.")

            coverage_recs = []
            if not tests_present:
                coverage_recs.append("No dedicated `/tests` or `/test` directory was found. 100% of codebase lacks coverage.")
            else:
                coverage_recs.append("Existing test file structure was detected, but detailed block-level execution metrics are not parsed.")

            mock_suggestions = []
            for dep in dependencies.keys():
                if dep in ("axios", "requests", "httpx"):
                    mock_suggestions.append(f"Mock HTTP requests made by `{dep}` library.")
                elif dep in ("pg", "sqlalchemy", "pymongo", "redis"):
                    mock_suggestions.append(f"Mock database/cache client queries for `{dep}`.")
            if not mock_suggestions:
                mock_suggestions = ["Information could not be determined from the available repository context."]

            edge_cases = []
            if largest_files:
                largest_path = get_item_path(largest_files[0])
                edge_cases.append(f"Check parameter validation, boundary values, and exception handling for operations in `{largest_path}`.")
            if not edge_cases:
                edge_cases = ["Information could not be determined from the available repository context."]

            fallback_json = {
                "unit_test_suggestions": unit_recs or ["Information could not be determined from the available repository context."],
                "integration_test_suggestions": integration_recs,
                "coverage_status": coverage_recs,
                "mock_opportunities": mock_suggestions,
                "edge_cases": edge_cases
            }

        elif task_key == "explain":
            entrypoints = []
            for f in largest_files:
                f_path = get_item_path(f)
                f_size = get_item_size(f)
                basename = f_path.split("/")[-1].split("\\")[-1]
                if basename in ("main.py", "app.py", "index.js", "App.tsx", "server.js", "manage.py", "index.ts"):
                    entrypoints.append(f"Entrypoint detected: `{f_path}` ({f_size} bytes)")
            if not entrypoints and largest_files:
                first_path = get_item_path(largest_files[0])
                first_size = get_item_size(largest_files[0])
                entrypoints.append(f"Primary candidate entrypoint: `{first_path}` ({first_size} bytes)")
            if not entrypoints:
                entrypoints = ["Information could not be determined from the available repository context."]

            arch_lines = []
            if primary_lang and primary_lang != "Unknown":
                arch_lines.append(f"Built primarily using `{primary_lang}` codebase structures.")
            if framework and framework != "None":
                arch_lines.append(f"Structured around a `{framework}` application architecture layout.")
            if not arch_lines:
                arch_lines = ["Information could not be determined from the available repository context."]

            important_modules = []
            for f in largest_files[:3]:
                f_path = get_item_path(f)
                important_modules.append(f"Module: `{f_path}`")
            if not important_modules:
                important_modules = ["Information could not be determined from the available repository context."]

            data_flow = "Information could not be determined from the available repository context."
            if framework in ("FastAPI", "Express", "Next.js", "Django", "Flask"):
                data_flow = f"As a {framework} application, incoming data flows through API route declarations, mapping request payloads directly to handler functions before returning database/JSON results."

            component_relationships = [
                "Core library imports and package declarations specify project boundaries.",
                "Database dependencies (if any) link relational structures with codebase modules."
            ]

            execution_flow = [
                "Starts at detected entry points and invokes helper libraries and model modules sequentially."
            ]

            fallback_json = {
                "high_level_architecture": arch_lines,
                "entry_points": entrypoints,
                "component_relationships": component_relationships,
                "important_modules": important_modules,
                "execution_flow": execution_flow,
                "data_flow": data_flow
            }

        # Build fallback model object using Pydantic defaults and repairs
        repaired_json = response_parser.repair_fields(fallback_json, schema_cls)
        fallback_model = schema_cls.model_validate(repaired_json)
        
        fallback_model.is_fallback = True
        completed_timestamp = time.time()
        
        # Build empty or mocked metadata block
        fallback_model.ai_metadata = AIMetadata(
            provider=active_provider,
            provider_used_after_failover="None",
            model="None",
            latency=completed_timestamp - started_timestamp,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            retry_count=settings.MAX_RETRIES,
            cache_hit=False,
            fallback_flag=True,
            request_id=request_id,
            started_timestamp=started_timestamp,
            completed_timestamp=completed_timestamp,
            estimated_cost=0.0
        )
        
        return fallback_model

ai_service = AIService()
