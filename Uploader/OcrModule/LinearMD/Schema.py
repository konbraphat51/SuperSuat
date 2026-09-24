"""What the stages of the LinearMD pipeline hand each other."""

from dataclasses import dataclass
from typing import Literal

# How a batch is transcribed: all of its pages, or only the gap between two others.
BatchKind = Literal["write", "fill"]


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
class PageBatch:
    """A run of pages sent to the model in one request.

    Attributes:
        index: The batch's position `x` in the document: even batches are
            written first, odd ones fill the gaps between them.
        first_page: The first page of the batch, 0-indexed.
        last_page: The last page of the batch, inclusive.
        written_pages: The pages this batch transcribes, in order. An odd
            batch shares its first and last page with the even batches around
            it, which are sent as context but not transcribed again.
    """

    index: int
    first_page: int
    last_page: int
    written_pages: tuple[int, ...]

    @property
    def kind(self) -> BatchKind:
        """Whether this batch writes all of its pages or fills a gap."""
        return "write" if self.index % 2 == 0 else "fill"

    @property
    def pages(self) -> range:
        """Every page sent with this batch, in order."""
        return range(self.first_page, self.last_page + 1)
