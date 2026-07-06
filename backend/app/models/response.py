from pydantic import BaseModel, Field
from typing import Optional

class ReviewResponse(BaseModel):
    job_id: str = Field(..., description="The unique UUID job ID")

class StatusResponse(BaseModel):
    status: str = Field(..., description="Current job status (e.g. running, completed, failed)")
    progress: int = Field(..., description="Progress percentage (0-100)")
    stage: str = Field(..., description="Current active pipeline stage description")

class ResultResponse(BaseModel):
    status: str = Field(..., description="Status of the result request (processing, completed, failed)")
    result: Optional[str] = Field(None, description="The final markdown analysis report, if ready")
