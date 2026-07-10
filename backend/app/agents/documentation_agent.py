from pydantic import BaseModel, Field
from typing import List, Dict, Any, Tuple
from app.agents.base_agent import BaseAgent
from app.core.config import settings

class DocItemSchema(BaseModel):
    file: str = Field(..., description="Target file path")
    docstring_or_readme: str = Field(..., description="Generated markdown documentation or code docstrings")

class DocumentationAgentSchema(BaseModel):
    missing_documentation: List[str] = Field(..., description="Files or folders needing docstrings or README files")
    generated_docs: List[DocItemSchema] = Field(..., description="Suggested generated documentation structures")
    confidence: float = Field(..., description="Documentation agent confidence score")

class DocumentationAgent(BaseAgent):
    """
    Formulates inline docstring comments or external markdown files to clarify modules.
    """
    def __init__(self):
        super().__init__("Documentation Agent", DocumentationAgentSchema)

    async def analyze_step(
        self,
        goal: str,
        step_description: str,
        code_context: str
    ) -> Tuple[DocumentationAgentSchema, Dict[str, Any]]:
        context_vars = {
            "goal": goal,
            "step_description": step_description,
            "code_context": code_context
        }
        system_prompt, user_prompt = self.render_prompts(context_vars, settings.PROMPT_VERSION_DOCUMENTATION)

        model_res, telemetry = await self.call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2
        )
        return model_res, telemetry
