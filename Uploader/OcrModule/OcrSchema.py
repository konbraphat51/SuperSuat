from dataclasses import dataclass
from typing import Literal, get_args

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

    def __post_init__(self):
        if self.block_type not in get_args(TEXT_BLOCK_TYPES):
            raise ValueError(f"Invalid block_type for OcrResultBlockText: {self.block_type}")

@dataclass
class OcrResultBlockImage(OcrResultBlock):
    page_number: int # the page whose pixel coordinates bounding_box is expressed in, 0-indexed
    bounding_box: tuple[int, int, int, int] # (x, y, width, height), in page_number's pixel space
    caption: str

    def __post_init__(self):
        self.block_type = "image"


@dataclass
class OcrResultSection(OcrResultBlock):
    section_content: list[OcrResultBlock] # can contain nested OcrResultSection instances

    def __post_init__(self):
        self.block_type = "section"

@dataclass
class OcrResult:
    root_section: OcrResultSection
