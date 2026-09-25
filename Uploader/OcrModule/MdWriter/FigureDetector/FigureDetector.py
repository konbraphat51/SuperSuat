"""Abstract base for finding the figures of a document's pages."""

import logging
from abc import ABC, abstractmethod

from PIL.Image import Image

from ...Blocked.PageParallel import DEFAULT_MAX_PARALLEL_PAGES, run_parallel
from ..Schema import DetectedFigure

logger = logging.getLogger(__name__)


class FigureDetector(ABC):
    """Finds the figure regions of page images, and nothing else.

    Everything that is not a figure - text, tables, formulas - is written out
    by the model from the page itself, so only the regions that cannot be
    written out as Markdown are detected here.

    A subclass only detects the figures of a single page; numbering them
    across the document in a stable order is the same for every model, so it
    lives here.

    Pages are detected several at a time. A subclass whose model does not take
    being called from several threads at once lowers MAX_PARALLEL_PAGES."""

    # Pages detected at once. Lower it in a subclass whose model cannot take it.
    MAX_PARALLEL_PAGES = DEFAULT_MAX_PARALLEL_PAGES

    def detect(self, pages: list[Image]) -> list[DetectedFigure]:
        """Every figure of the pages, in page order, each with a unique id."""
        pages_figures = run_parallel(
            lambda numbered_page: self._detect_page(*numbered_page),
            list(enumerate(pages)),
            self.MAX_PARALLEL_PAGES,
            progress_label="detecting figures",
        )

        figures = [figure for page_figures in pages_figures for figure in page_figures]

        # ids are handed out once every page is in, so they do not depend on
        # the order the pages happened to finish in
        for block_id, figure in enumerate(figures):
            figure.block_id = block_id

        logger.info(
            "%s found %d figure(s) in %d page(s)",
            type(self).__name__,
            len(figures),
            len(pages),
        )
        return figures

    def _detect_page(self, page_index: int, page: Image) -> list[DetectedFigure]:
        """The figures of one page, ordered top-to-bottom then left-to-right."""
        figures = [
            # the id is reassigned to a document-wide value once every page is in
            DetectedFigure(block_id=0, page_index=page_index, bounding_box=box)
            for box in self._detect_page_figures(page)
        ]
        figures.sort(
            key=lambda figure: (figure.bounding_box[1], figure.bounding_box[0])
        )
        return figures

    @abstractmethod
    def _detect_page_figures(self, page: Image) -> list[tuple[int, int, int, int]]:
        """The boxes of the figures this model detects in one page.

        Boxes are `(x, y, width, height)`. Order does not matter: `detect()`
        sorts them into a stable, top-to-bottom order itself."""
        raise NotImplementedError
