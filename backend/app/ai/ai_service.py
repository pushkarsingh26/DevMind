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

        # Render empty chunks prompt to count base prompt overhead tokens
        base_sys_p, base_usr_p = prompt_builder.build_prompts(task_key, metadata_dict, [])
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
        system_prompt, user_prompt = prompt_builder.build_prompts(task_key, metadata_dict, budgeted_chunks)

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
                logger.warning(f"AIService: Skipping chain provider: {val_err}")
                continue

            if not api_key or "api_key_here" in api_key:
                logger.warning(f"AIService: API key missing for provider '{current_provider}'. Skipping.")
                continue

            provider_used_after_failover = current_provider if current_provider != active_provider else None
            logger.info(f"AIService: Requesting LLM response from provider '{current_provider}' / model '{model_name}'")
            
            client = provider_factory.get_client(current_provider)
            
            # Retry loop for this provider
            retry_count = 0
            for attempt in range(settings.MAX_RETRIES):
                retry_count = attempt
                t_attempt_start = time.time()
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
                    logger.warning(
                        f"AIService: Request failed on provider '{current_provider}' (attempt {attempt + 1}/{settings.MAX_RETRIES}). "
                        f"Error: {err}"
                    )
                    
                    # Exponential backoff with jitter
                    if attempt < settings.MAX_RETRIES - 1:
                        sleep_time = (2 ** attempt) + random.uniform(0.1, 0.5)
                        await asyncio.sleep(sleep_time)

            if final_response_obj:
                # Successfully received response, exit provider chain loop
                break
            else:
                logger.error(
                    f"AIService: All retries failed for provider '{current_provider}'. "
                    f"Progressing with failover logic."
                )

        if final_response_obj:
            # Log successful operation details only (Never log code or responses)
            logger.info(
                f"AIService: Analysis successful. Request ID: {request_id}. "
                f"Used Provider: {provider_used_after_failover or active_provider}. Model: {final_response_obj.ai_metadata.model}. "
                f"Latency: {final_response_obj.ai_metadata.latency:.3f}s. Tokens: {final_response_obj.ai_metadata.total_tokens}."
            )
            return final_response_obj

        # 8. All failover providers failed, run Heuristic Fallback
        logger.error(
            f"AIService: Final Outage! All failover chain providers failed to resolve request. "
            f"Activating graceful fallback. Exception: {last_exception}"
        )

        # Build fallback model object using Pydantic defaults and repairs
        fallback_json = response_parser.repair_fields({}, schema_cls)
        fallback_model = schema_cls.model_validate(fallback_json)
        
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
