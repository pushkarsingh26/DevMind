from pydantic import BaseModel, Field
from app.core.constants import TaskType

class ReviewRequest(BaseModel):
    repo_url: str = Field(..., description="The GitHub Repository URL to scan")
    task: TaskType = Field(TaskType.REVIEW, description="The analysis task to perform")
