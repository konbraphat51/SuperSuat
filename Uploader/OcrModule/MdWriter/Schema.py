"""What the stages of the MdWriter pipeline hand each other."""

from dataclasses import dataclass
from typing import Literal

from PIL.Image import Image

# How a page is transcribed: on its own, or as the gap between two written pages.
PageKind = Literal["write", "fill"]


@dataclass
class DetectedFigure:
    """One figure region of a page, as the FigureDetector found it.

    Satisfies BoxedBlock, so BlockRenderer draws it as it is.

    Attributes:
        block_id: A unique identifier for the figure within the document.
        page_index: The page the figure is on, 0-indexed.
        bounding_box: The figure's box in (x, y, width, height) format.
    """

    block_id: int
    page_index: int
    bounding_box: tuple[int, int, int, int]


@dataclass(frozen=True)
class PageTask:
    """One page sent to the model in one request.

    Attributes:
        page_index: The page to transcribe, 0-indexed. Pages at even indices
            (the 1st, 3rd, ... page) are written first, on their own; the
            pages between them are filled in afterwards, with the Markdown
            of the pages either side in view.
    """

    page_index: int

    @property
    def kind(self) -> PageKind:
        """Whether this page is written on its own or fills a gap."""
        return "write" if self.page_index % 2 == 0 else "fill"


@dataclass
class MarkdownDraft:
    """A document written out as Markdown, before it is read into the tree.

    Attributes:
        markdown: The whole document, the pages stitched together.
        figures: Every figure detected in the document.
        rendered_pages: Every page as the model saw it, figures drawn on.
    """

    markdown: str
    figures: list[DetectedFigure]
    rendered_pages: list[Image]
