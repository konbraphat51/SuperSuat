from dataclasses import dataclass
from typing import Literal

TEXT_BLOCK_TYPES = Literal[
    "paragraph",
    "heading",
    "list_item",
    "document_index",
    "note",
    "code",
    "math",
]

@dataclass
class OcrResultBlock:
    block_type: TEXT_BLOCK_TYPES | Literal["image"]
    existing_pages: list[int]   # Pages that this block is present on. 0-indexed
    block_index: int # this is unique within the document

@dataclass
class OcrResultBlockText(OcrResultBlock):
    text: str
    text_type: TEXT_BLOCK_TYPES

@dataclass
class OcrResultBlockImage(OcrResultBlock):
    image_data: bytes
    caption: str


@dataclass
class OcrResultSection:
    section_content: list[OcrResultBlock]
    child_sections: list["OcrResultSection"]
    section_index: int # this is unique within the document


@dataclass
class OcrResult:
    root_section: OcrResultSection
