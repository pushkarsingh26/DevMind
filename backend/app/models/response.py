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
    ai_output: Optional[dict] = Field(None, description="The raw structured AI evaluation metrics and suggestions")
    repository: Optional[dict] = Field(None, description="Structured repository parameters")
    metadata: Optional[dict] = Field(None, description="Structured metadata scanned details")
    statistics: Optional[dict] = Field(None, description="Structured file/directory counts and sizes")
    chunks: Optional[list] = Field(None, description="Raw list of chunks retrieved during reasoning")
