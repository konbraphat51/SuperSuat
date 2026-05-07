from pydantic import BaseModel, Field
from typing import Literal

class DocumentAnalysis(BaseModel):
    # heading level -> styling name description
    heading_style_map: dict[int, str] = {}

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
