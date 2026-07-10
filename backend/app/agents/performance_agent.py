from pydantic import BaseModel, Field
from typing import List, Dict, Any, Tuple
from app.agents.base_agent import BaseAgent
from app.core.config import settings

class BottleneckSchema(BaseModel):
    description: str = Field(..., description="Details of performance bottleneck")
    file: str = Field(..., description="Affected file path")
    impact: str = Field(..., description="Estimated impact: High, Medium, Low")

class PerformanceAgentSchema(BaseModel):
    bottlenecks: List[BottleneckSchema] = Field(..., description="Observed bottlenecks")
    recommendations: List[str] = Field(..., description="Performance enhancements")
    confidence: float = Field(..., description="Evaluation confidence score")

class PerformanceAgent(BaseAgent):
    """
    Identifies resource leaks, non-cached queries, unbuffered operations, and bottlenecks.
    """
    def __init__(self):
        super().__init__("Performance Agent", PerformanceAgentSchema)

    async def analyze_step(
        self,
        goal: str,
        step_description: str,
        code_context: str
    ) -> Tuple[PerformanceAgentSchema, Dict[str, Any]]:
        context_vars = {
            "goal": goal,
            "step_description": step_description,
            "code_context": code_context
        }
        system_prompt, user_prompt = self.render_prompts(context_vars, settings.PROMPT_VERSION_PERFORMANCE)

        model_res, telemetry = await self.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2
        )
        return model_res, telemetry
