from typing import TypedDict
from PIL.Image import Image
from langchain_core.messages import BaseMessage

class AnalysisState(TypedDict):
    # =inputs=
    images: list[Image]

    # =outputs=
    heading_style_map: dict[int, str]
    "1-indexed heading -> style description"

    ocr_rules: str
    "A unified OCR rule description"

    # =persistence=
    messages: list[BaseMessage]

class PageCheckResult(TypedDict):
    page_passed: bool
    "Whether the page layout is covered in the layout document and can pass to OCR transcription."

    unknown_layout_styles: str | None
    "If there is unknown layout style that may cause inconsistency in inter-page OCR results, "
    "specify and describe the unknown layout style so that the layout analyst agent can update the layout."
