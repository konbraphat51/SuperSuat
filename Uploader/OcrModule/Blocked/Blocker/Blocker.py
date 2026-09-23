"""Abstract base for the layout stage of the OCR pipeline."""

import logging
from abc import ABC, abstractmethod

from PIL.Image import Image

from ..PageParallel import DEFAULT_MAX_PARALLEL_PAGES, map_pages
from ..Schema import Block, BlockerResult, BlockType

logger = logging.getLogger(__name__)


class Blocker(ABC):
    """Splits page images into the regions worth reading.

    A subclass only detects the regions of a single page; turning that into a
    document-wide, uniquely-identified, stably-ordered `BlockerResult` is the
    same for every implementation, so it lives here instead of being repeated
    in each one.

    Pages are detected several at a time. A subclass whose model does not take
    being called from several threads at once, or does not fit several pages
    in memory, lowers MAX_PARALLEL_PAGES."""

    # Pages detected at once. Lower it in a subclass whose model cannot take it.
    MAX_PARALLEL_PAGES = DEFAULT_MAX_PARALLEL_PAGES

    def block(self, pages: list[Image]) -> BlockerResult:
        """Detects blocks of text, math, images, and tables in the page images."""
        pages_blocks = map_pages(
            lambda numbered_page: self._block_page(*numbered_page),
            list(enumerate(pages)),
            self.MAX_PARALLEL_PAGES,
        )

        blocks = [block for page_blocks in pages_blocks for block in page_blocks]

        # ids are handed out once every page is in, so they do not depend on
        # the order the pages happened to finish in
        for block_id, block in enumerate(blocks):
            block.block_id = block_id

        logger.info(
            "%s blocked %d pages into %d blocks",
            type(self).__name__,
            len(pages),
            len(blocks),
        )
        return BlockerResult(blocks=blocks)

    def _block_page(self, page_index: int, page: Image) -> list[Block]:
        """Every block of one page, ordered top-to-bottom then left-to-right.

        The page number is 0-indexed, as elsewhere in the OCR module."""
        elements = self._detect_page(page)

        blocks = [
            Block(
                # Reassigned to a document-wide value once every page is in.
                block_id=0,
                block_type=block_type,
                page_index=page_index,
                bounding_box=bounding_box,
            )
            for block_type, bounding_box in elements
        ]
        blocks.sort(key=lambda block: (block.bounding_box[1], block.bounding_box[0]))
        return blocks

    @abstractmethod
    def _detect_page(
        self, page: Image
    ) -> list[tuple[BlockType, tuple[int, int, int, int]]]:
        """The (block type, bounding box) pairs this model detects in one page.

        Bounding boxes are `(x, y, width, height)`. Order does not matter:
        `block()` sorts them into a stable, top-to-bottom order itself."""
        raise NotImplementedError
