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
    block_type: TEXT_BLOCK_TYPES | Literal["image", "section"]
    existing_pages: list[int]   # Pages that this block is present on. 0-indexed
    block_index: int # this is unique within the document

@dataclass
class OcrResultBlockText(OcrResultBlock):
    text: str

@dataclass
class OcrResultBlockImage(OcrResultBlock):
    bounding_box: tuple[int, int, int, int] # (x, y, width, height)
    caption: str


@dataclass
class OcrResultSection(OcrResultBlock):
    section_content: list[OcrResultBlock] # can contain nested OcrResultSection instances


@dataclass
class OcrResult:
    root_section: OcrResultSection
