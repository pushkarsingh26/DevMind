from pydantic import BaseModel, Field
from typing import List, Dict, Any, Tuple
from app.agents.base_agent import BaseAgent
from app.core.config import settings

class RefactoringItem(BaseModel):
    file: str = Field(..., description="Target file path to modify")
    original_code: str = Field(..., description="The original section of code to replace")
    refactored_code: str = Field(..., description="The proposed refactored replacement code")
    reason: str = Field(..., description="Detailed explanation of why this change is suggested")
    impact: str = Field(..., description="Expected impact")

class RefactorAgentSchema(BaseModel):
    refactorings: List[RefactoringItem] = Field(default=[], description="List of proposed refactorings")
    diff: str = Field(default="", description="A standard unified git diff preview of modifications")
    confidence: float = Field(..., description="Agent confidence (0.0 - 1.0)")
    risk_level: str = Field(default="Low", description="Risk level: High, Medium, Low")
    expected_impact: str = Field(default="Improves codebase safety", description="Expected impact summary")

class RefactorAgent(BaseAgent):
    """
    Generates structured code improvements, writes diff previews, and checks safety.
    """
    def __init__(self):
        super().__init__("Refactor Agent", RefactorAgentSchema)

    async def analyze_step(
        self,
        goal: str,
        step_description: str,
        code_context: str
    ) -> Tuple[RefactorAgentSchema, Dict[str, Any]]:
        context_vars = {
            "goal": goal,
            "step_description": step_description,
            "code_context": code_context
        }
        system_prompt, user_prompt = self.render_prompts(context_vars, settings.PROMPT_VERSION_REFACTOR)

        model_res, telemetry = await self.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1
        )
        return model_res, telemetry
