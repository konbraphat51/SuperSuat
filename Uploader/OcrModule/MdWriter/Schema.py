"""What the stages of the MdWriter pipeline hand each other."""

from dataclasses import dataclass

from PIL.Image import Image


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
class CorrectedFigure:
    """One figure of a page as a correction redraws it.

    Attributes:
        block_id: The id of the detected figure this box replaces, or None
            for a figure the detector missed, which is given a new id.
        bounding_box: The figure's box in (x, y, width, height) format.
    """

    block_id: int | None
    bounding_box: tuple[int, int, int, int]


@dataclass(frozen=True)
class PageTask:
    """One page sent to the model in one request.

    Attributes:
        page_index: The page to transcribe, 0-indexed.
        page_count: How many pages the document has.
    """

    page_index: int
    page_count: int

    @property
    def has_previous(self) -> bool:
        """Whether a page comes before this one, which it may continue."""
        return self.page_index > 0

    @property
    def has_next(self) -> bool:
        """Whether a page comes after this one, which may continue it."""
        return self.page_index < self.page_count - 1


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
