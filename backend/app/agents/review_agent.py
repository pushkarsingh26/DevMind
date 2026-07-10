from pydantic import BaseModel, Field
from typing import List, Dict, Any, Tuple
from app.agents.base_agent import BaseAgent
from app.core.config import settings

class ReviewAgentSchema(BaseModel):
    strengths: List[str] = Field(..., description="Observed codebase design strengths")
    weaknesses: List[str] = Field(..., description="Design patterns code quality issues detected")
    recommendations: List[str] = Field(..., description="Refactoring or pattern improvements suggested")
    confidence: float = Field(..., description="Review confidence score (0.0 - 1.0)")

class ReviewAgent(BaseAgent):
    """
    Evaluates codebase structural design patterns, architectures, and general health.
    """
    def __init__(self):
        super().__init__("Review Agent", ReviewAgentSchema)

    async def analyze_step(
        self,
        goal: str,
        step_description: str,
        code_context: str
    ) -> Tuple[ReviewAgentSchema, Dict[str, Any]]:
        context_vars = {
            "goal": goal,
            "step_description": step_description,
            "code_context": code_context
        }
        system_prompt, user_prompt = self.render_prompts(context_vars, settings.PROMPT_VERSION_REVIEW)

        model_res, telemetry = await self.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2
        )
        return model_res, telemetry
