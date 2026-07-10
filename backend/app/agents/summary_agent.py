from pydantic import BaseModel, Field
from typing import List, Dict, Any, Tuple
from app.agents.base_agent import BaseAgent
from app.core.config import settings

class SummaryAgentSchema(BaseModel):
    executive_summary: str = Field(..., description="High-level markdown summary of the workflow run")
    key_findings: List[str] = Field(default=[], description="Bullet points of key outcomes or improvements")
    recommendations: List[str] = Field(default=[], description="Bullet points of suggestions or action items")
    confidence: float = Field(..., description="Overall summary confidence rating")

class SummaryAgent(BaseAgent):
    """
    Synthesizes the execution history and individual outputs into a master report.
    """
    def __init__(self):
        super().__init__("Summary Agent", SummaryAgentSchema)

    async def analyze_history(
        self,
        goal: str,
        execution_context_logs: str
    ) -> Tuple[SummaryAgentSchema, Dict[str, Any]]:
        context_vars = {
            "goal": goal,
            "logs": execution_context_logs
        }
        system_prompt, user_prompt = self.render_prompts(context_vars, settings.PROMPT_VERSION_SUMMARY)

        model_res, telemetry = await self.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2
        )
        return model_res, telemetry
