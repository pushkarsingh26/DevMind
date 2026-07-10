from pydantic import BaseModel, Field
from typing import List, Dict, Any, Tuple
from app.agents.base_agent import BaseAgent
from app.core.config import settings

class TestSuggestionSchema(BaseModel):
    file: str = Field(..., description="Target file that needs test coverage")
    test_type: str = Field(..., description="Test type: Unit, Integration, E2E")
    description: str = Field(..., description="Suggested test details and edge cases to test")

class TestingAgentSchema(BaseModel):
    untested_files: List[str] = Field(..., description="List of source files lacking coverage")
    test_suggestions: List[TestSuggestionSchema] = Field(..., description="Actionable test details suggestions")
    confidence: float = Field(..., description="Testing audit confidence score")

class TestingAgent(BaseAgent):
    """
    Scans files, outlines unit testing gaps, and writes mock recommendations.
    """
    def __init__(self):
        super().__init__("Testing Agent", TestingAgentSchema)

    async def analyze_step(
        self,
        goal: str,
        step_description: str,
        code_context: str
    ) -> Tuple[TestingAgentSchema, Dict[str, Any]]:
        context_vars = {
            "goal": goal,
            "step_description": step_description,
            "code_context": code_context
        }
        system_prompt, user_prompt = self.render_prompts(context_vars, settings.PROMPT_VERSION_TESTING)

        model_res, telemetry = await self.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2
        )
        return model_res, telemetry
