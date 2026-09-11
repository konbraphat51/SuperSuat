from dataclasses import dataclass
from typing import Literal


@dataclass
class OcrResultBlock:
    block_type: Literal[
        "text",
        "image",
        "table",
        "equation",
        "footer",
        "section",
    ]
    existing_pages: list[int]   # Pages that this block is present on. 0-indexed
    block_index: int # this is unique within the document

@dataclass
class OcrResultBlockText(OcrResultBlock):
    text: str
    text_type: Literal[
        "paragraph",
        "heading",
        "list_item",
        "document_index",
        "note",
        "code",
        "math",
    ]


@dataclass
class OcrResultBlockImage(OcrResultBlock):
    image_data: bytes
    caption: str


@dataclass
class OcrResultSection:
    section_content: list[OcrResultBlock]
    child_sections: list["OcrResultSection"]


@dataclass
class OcrResult:
    blocks: list[OcrResultBlock]
