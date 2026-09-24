"""The document tree an OCR run produces."""

from dataclasses import dataclass
from typing import Literal, get_args

TEXT_BLOCK_TYPES = Literal[
    "paragraph",  # main body text
    "heading",  # any heading, including chapter titles and the document's own title
    "document_index",  # page numbers, running heads - anything not part of the content
    "note",  # footnote, endnote, sidenote, column note, etc.
    "code",  # source code or pseudocode
    "math",  # formula or equation, in KaTeX format
    "table",  # a table, in Markdown format
]


@dataclass
class OcrResultBlock:
    """One piece of the document, of whatever kind."""

    block_type: TEXT_BLOCK_TYPES | Literal["figure", "section"]
    existing_pages: list[int]  # pages this block appears on, 0-indexed
    block_index: int  # unique within the document


@dataclass
class OcrResultBlockText(OcrResultBlock):
    """A block of text, of one of the TEXT_BLOCK_TYPES."""

    text: str

    def __post_init__(self) -> None:
        if self.block_type not in get_args(TEXT_BLOCK_TYPES):
            raise ValueError(
                f"Invalid block_type for OcrResultBlockText: {self.block_type}"
            )


@dataclass
class OcrResultBlockFigure(OcrResultBlock):
    """A photo, diagram, or illustration, as a region of one page image."""

    page_index: int  # 0-indexed; the page bounding_box is in the pixel space of
    bounding_box: tuple[int, int, int, int]  # (x, y, width, height)
    caption: str

    def __post_init__(self) -> None:
        self.block_type = "figure"


@dataclass
class OcrResultSection(OcrResultBlock):
    """A run of blocks belonging together, nestable to mirror the document."""

    section_content: list[OcrResultBlock]

    def __post_init__(self) -> None:
        self.block_type = "section"


@dataclass
class OcrResult:
    """A whole document, as one tree."""

    root_section: OcrResultSection
