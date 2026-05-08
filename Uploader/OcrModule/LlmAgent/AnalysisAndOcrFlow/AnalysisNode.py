from __future__ import annotations
from pydantic import BaseModel, Field

class AnalysisResult(BaseModel):
    heading_styles: dict[int, str] = Field(
        description="A dictionary mapping heading levels to their corresponding styles descriptions."
    )
