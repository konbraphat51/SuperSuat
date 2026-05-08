from pydantic import BaseModel, Field
from typing import Literal


class DocumentAnalysis(BaseModel):
    # heading level -> styling name description
    heading_style_map: dict[int, str] = Field(
        description="A map of heading level to style description. For example, {1: 'bold and centered', 2: 'bold and left-aligned', ...}"
    )


class OcrResultBlock(BaseModel):
    block_type: Literal[
        "text", "image", "table", "equation", "footer", "section"
    ] = Field(description="The type of the OCR result block.")


class OcrResultBlockText(OcrResultBlock):
    text: str


class OcrResultBlockImage(OcrResultBlock):
    image_data: bytes
    caption: str


class OcrResultBlockTable(OcrResultBlock):
    text: str  # in Markdown format
    caption: str


class OcrResultBlockEquation(OcrResultBlock):
    text: str  # in LaTeX format
    caption: str


class OcrResultBlockFooter(OcrResultBlock):
    text: str


class OcrResultBlockSection(OcrResultBlock):
    text: str
    level: int


class OcrResult(BaseModel):
    blocks: list[OcrResultBlock]


class PageOcrResult(BaseModel):
    page_num: int
    markdown: str
    figures: list[tuple[tuple[float, float, float, float], str]]
    status: Literal["pending", "done", "escalated"] = "pending"
    unknown_layout_description: str = ""
