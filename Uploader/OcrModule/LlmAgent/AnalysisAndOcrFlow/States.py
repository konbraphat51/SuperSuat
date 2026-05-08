from pydantic import BaseModel, Field
from typing import Literal


class DocumentAnalysis(BaseModel):
    # heading level -> styling name description
    heading_style_map: dict[int, str] = Field(
        description="A map of heading level to style description. For example, {1: 'bold and centered', 2: 'bold and left-aligned', ...}"
    )

class SingleLayoutCheckResult(BaseModel):
    has_unknown_layout: bool = Field(description="Whether there is an unknown layout style in the page.")
    unknown_layout_description: str = Field(
        description=(
            "A detailed description of the unknown layout style if there is, or an empty string if there is not."
            "The description should be detailed enough for layout analyst agent to update the layout analysis document."
        )
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
