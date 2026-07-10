from pydantic import BaseModel, Field
from typing import List, Dict, Any, Tuple
from app.agents.base_agent import BaseAgent
from app.core.config import settings

class VulnerabilitySchema(BaseModel):
    severity: str = Field(..., description="Vulnerability severity level: Critical, High, Medium, Low")
    description: str = Field(..., description="Details of the vulnerability")
    file: str = Field(..., description="Affected file path")
    line: int = Field(..., description="Line number of concern")

class SecurityAgentSchema(BaseModel):
    vulnerabilities: List[VulnerabilitySchema] = Field(..., description="Detected security items")
    security_score: int = Field(..., description="Calculated security rating score (0 - 100)")
    recommendations: List[str] = Field(..., description="Actionable security remediation fixes")
    confidence: float = Field(..., description="Analysis confidence (0.0 - 1.0)")

class SecurityAgent(BaseAgent):
    """
    Scans code blocks for security flaws, bare exceptions, JWT bugs, and data leaks.
    """
    def __init__(self):
        super().__init__("Security Agent", SecurityAgentSchema)

    async def analyze_step(
        self,
        goal: str,
        step_description: str,
        code_context: str
    ) -> Tuple[SecurityAgentSchema, Dict[str, Any]]:
        context_vars = {
            "goal": goal,
            "step_description": step_description,
            "code_context": code_context
        }
        system_prompt, user_prompt = self.render_prompts(context_vars, settings.PROMPT_VERSION_SECURITY)

        model_res, telemetry = await self.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1
        )
        return model_res, telemetry
