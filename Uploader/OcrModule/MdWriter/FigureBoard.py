"""The document's figures and its pages with them drawn on, correctable page by page."""

import threading
from collections.abc import Sequence

from PIL.Image import Image

from ..Blocked.Blocker.BlockRenderer import BlockRenderer
from .Schema import CorrectedFigure, DetectedFigure


class FigureBoard:
    """Holds every figure of the document, and draws each page with its own.

    The pages are written at once, each on its own thread, and a page may have
    its figures corrected while it is written; so the figures are only read and
    replaced here, under one lock. A corrected page is drawn again the next
    time it is asked for. A figure a correction adds takes an id no figure of
    the document has ever had, so an id the model has seen never changes
    meaning."""

    def __init__(
        self,
        pages: Sequence[Image],
        figures: Sequence[DetectedFigure],
        renderer: BlockRenderer | None = None,
    ) -> None:
        """
        Args:
            pages: Every page of the document, as scanned.
            figures: Every figure of the document, as the detector found them.
            renderer: Draws the figures and their ids onto the pages.
        """
        self._pages = list(pages)
        self._renderer = renderer or BlockRenderer()
        self._lock = threading.Lock()
        self._figures: dict[int, list[DetectedFigure]] = {}
        self._rendered: dict[int, Image] = {}
        self._next_id = max((figure.block_id for figure in figures), default=-1) + 1

        for figure in figures:
            self._figures.setdefault(figure.page_index, []).append(figure)

    @property
    def page_count(self) -> int:
        """How many pages the document has."""
        return len(self._pages)

    @property
    def figures(self) -> list[DetectedFigure]:
        """Every figure of the document, in page order."""
        with self._lock:
            return [
                figure
                for page_index in sorted(self._figures)
                for figure in self._figures[page_index]
            ]

    def page(self, page_index: int) -> Image:
        """The page as scanned, nothing drawn on."""
        return self._pages[page_index]

    def figures_on(self, page_index: int) -> list[DetectedFigure]:
        """The figures of one page, top to bottom."""
        with self._lock:
            return list(self._figures.get(page_index, []))

    def figure_ids_on(self, page_index: int) -> list[int]:
        """The ids of the figures of one page, top to bottom."""
        return [figure.block_id for figure in self.figures_on(page_index)]

    def rendered(self, page_index: int) -> Image:
        """The page with its figures' boxes and ids drawn on."""
        with self._lock:
            if page_index not in self._rendered:
                self._rendered[page_index] = self._renderer.render_page(
                    self._pages[page_index], self._figures.get(page_index, [])
                )
            return self._rendered[page_index]

    def rendered_pages(self) -> list[Image]:
        """Every page with its figures drawn on, in page order."""
        return [self.rendered(page_index) for page_index in range(self.page_count)]

    def replace(
        self, page_index: int, corrections: Sequence[CorrectedFigure]
    ) -> list[DetectedFigure]:
        """Makes `corrections` the whole of a page's figures, and returns them.

        A correction naming a figure of the page keeps its id; one naming no
        figure, or one of another page, is given a new id.
        """
        with self._lock:
            kept_ids = {figure.block_id for figure in self._figures.get(page_index, [])}
            figures: list[DetectedFigure] = []

            for correction in corrections:
                block_id = correction.block_id
                if block_id is None or block_id not in kept_ids:
                    block_id = self._next_id
                    self._next_id += 1
                # an id stays with one box, even when a correction names it twice
                kept_ids.discard(block_id)
                figures.append(
                    DetectedFigure(block_id, page_index, correction.bounding_box)
                )

            figures.sort(
                key=lambda figure: (figure.bounding_box[1], figure.bounding_box[0])
            )
            self._figures[page_index] = figures
            self._rendered.pop(page_index, None)
            return list(figures)
