from pydantic import BaseModel, Field
from typing import Literal

class DocumentAnalysis(BaseModel):
    # heading level -> styling name description
    heading_style_map: dict[int, str] = Field(
        description="A map of heading level to style description. For example, {1: 'bold and centered', 2: 'bold and left-aligned', ...}"
    )

class PageOcrResult(BaseModel):
    page_num: int
    markdown: str
    figures: list[
        tuple[
            tuple[float, float, float, float],
            str
        ]
    ]
    status: Literal["pending", "done", "escalated"] = "pending"
    unknown_layout_description: str = ""
