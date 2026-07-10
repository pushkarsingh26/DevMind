from pydantic import BaseModel, Field
from typing import List, Dict, Any, Tuple
from app.agents.base_agent import BaseAgent
from app.core.config import settings

class RepositoryAgentSchema(BaseModel):
    findings: List[str] = Field(..., description="Findings about codebase structure or files discovered")
    files_analyzed: List[str] = Field(..., description="List of file paths inspected")
    confidence: float = Field(..., description="Confidence score")

class RepositoryAgent(BaseAgent):
    """
    Locates target components, reads packages, and traces file patterns.
    """
    def __init__(self):
        super().__init__("Repository Agent", RepositoryAgentSchema)

    async def analyze_step(
        self,
        goal: str,
        step_description: str,
        code_context: str
    ) -> Tuple[RepositoryAgentSchema, Dict[str, Any]]:
        context_vars = {
            "goal": goal,
            "step_description": step_description,
            "code_context": code_context
        }
        system_prompt, user_prompt = self.render_prompts(context_vars, settings.PROMPT_VERSION_REPOSITORY)

        model_res, telemetry = await self.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2
        )
        return model_res, telemetry
