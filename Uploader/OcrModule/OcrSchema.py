"""The document tree an OCR run produces."""

from dataclasses import dataclass, field
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

    block_type: TEXT_BLOCK_TYPES | Literal["figure", "section", "table_of_contents"]
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
class TableOfContentsEntry:
    """One entry of a table of contents, with the entries nested under it."""

    section_number: str | None  # as printed, such as "1.2"; None if unnumbered
    title: str
    page_number: str | None  # as printed, such as "12" or "iv"; None if not printed
    children: list["TableOfContentsEntry"] = field(default_factory=list)


@dataclass
class OcrResultBlockTableOfContents(OcrResultBlock):
    """A table of contents printed in the document, as a tree of its entries."""

    entries: list[TableOfContentsEntry]  # the outermost entries, in printed order

    def __post_init__(self) -> None:
        self.block_type = "table_of_contents"


@dataclass
class OcrResultSection(OcrResultBlock):
    """A run of blocks belonging together, nestable to mirror the document."""

    section_content: list[OcrResultBlock]

    def __post_init__(self) -> None:
        self.block_type = "section"

    def recompute_existing_pages(self) -> list[int]:
        """Sets this section's existing_pages, and every nested section's, to
        the pages of its contents, and returns this section's."""
        pages: set[int] = set()

        for block in self.section_content:
            if isinstance(block, OcrResultSection):
                pages.update(block.recompute_existing_pages())
            else:
                pages.update(block.existing_pages)

        self.existing_pages = sorted(pages)

        return self.existing_pages


@dataclass
class OcrResult:
    """A whole document, as one tree."""

    root_section: OcrResultSection
