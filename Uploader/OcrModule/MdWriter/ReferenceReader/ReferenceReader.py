"""Abstract base for reading the plain text of a document's pages with a local OCR."""

import logging
from abc import ABC, abstractmethod

from PIL.Image import Image

from ...Blocked.PageParallel import run_parallel

logger = logging.getLogger(__name__)


class ReferenceReader(ABC):
    """Reads the text of page images, paragraph by paragraph, without structure.

    A conventional OCR reads characters faithfully but knows nothing of
    Markdown; the model is given its text as a reference to check the
    characters it writes against, and the pipeline uses it to tell a page the
    model misread from one it read well.

    A subclass only reads a single page. Pages are read MAX_PARALLEL_PAGES at
    a time; a subclass whose model does not take several threads lowers it."""

    # Pages read at once. One is the safe default for a model on a single GPU.
    MAX_PARALLEL_PAGES = 1

    def read(self, pages: list[Image]) -> list[str]:
        """The text of every page, in page order, paragraphs separated by blank lines."""
        texts = run_parallel(
            self._read_page,
            pages,
            self.MAX_PARALLEL_PAGES,
            progress_label="reading reference",
        )
        logger.info(
            "%s read %d characters from %d page(s)",
            type(self).__name__,
            sum(len(text) for text in texts),
            len(pages),
        )
        return texts

    @abstractmethod
    def _read_page(self, page: Image) -> str:
        """The text of one page in its reading order, running heads and page
        numbers left out, paragraphs separated by blank lines.

        Args:
            page: The page as it was scanned, with nothing drawn on it.
        """
