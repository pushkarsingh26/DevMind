from pydantic import BaseModel, Field
from typing import List, Dict, Any, Tuple
from app.agents.base_agent import BaseAgent
from app.core.config import settings

class PlanStepSchema(BaseModel):
    name: str = Field(..., description="Step name, e.g., 'Inspect JWT Validation'")
    agent: str = Field(..., description="Target agent name")
    description: str = Field(..., description="Description of the step actions")
    expected_output: str = Field(..., description="Expected output details")

class ExecutionPlanSchema(BaseModel):
    plan: List[PlanStepSchema] = Field(..., description="Sequential list of plan steps")
    rationale: str = Field(..., description="Reasoning for the structured plan")
    confidence: float = Field(..., description="Estimated planning confidence (0.0 - 1.0)")

class PlannerAgent(BaseAgent):
    """
    Formulates a structured execution plan based on the developer's natural language goal.
    """
    def __init__(self):
        super().__init__("Planner Agent", ExecutionPlanSchema)

    async def plan_goal(
        self,
        goal: str,
        repository_metadata: Dict[str, Any]
    ) -> Tuple[ExecutionPlanSchema, Dict[str, Any]]:
        """
        Generates a sequence of execution steps matching the repository metadata framework.
        """
        context_vars = {
            "goal": goal,
            "primary_language": repository_metadata.get('primary_language', 'Unknown'),
            "framework": repository_metadata.get('framework', 'None'),
            "total_files": repository_metadata.get('total_files', 0),
            "dependencies": list(repository_metadata.get('dependencies', {}).keys())[:15],
            "entrypoints": [f.get('path') for f in repository_metadata.get('largest_files', [])[:3]] if isinstance(repository_metadata.get('largest_files'), list) else []
        }
        system_prompt, user_prompt = self.render_prompts(context_vars, settings.PROMPT_VERSION_PLANNER)

        plan_model, telemetry = await self.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1
        )
        return plan_model, telemetry
