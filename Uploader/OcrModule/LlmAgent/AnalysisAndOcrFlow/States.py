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
