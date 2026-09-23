"""Abstract base for the layout stage of the OCR pipeline."""

import logging
from abc import ABC, abstractmethod

from PIL.Image import Image

from ..Schema import Block, BlockerResult, BlockType

logger = logging.getLogger(__name__)


class Blocker(ABC):
    """Splits page images into the regions worth reading.

    A subclass only detects the regions of a single page; turning that into a
    document-wide, uniquely-identified, stably-ordered `BlockerResult` is the
    same for every implementation, so it lives here instead of being repeated
    in each one."""

    def block(self, pages: list[Image]) -> BlockerResult:
        """Detects blocks of text, math, images, and tables in the page images."""
        blocks: list[Block] = []
        for page_index, page in enumerate(pages):
            blocks.extend(self._block_page(page, page_index))

        for block_id, block in enumerate(blocks):
            block.block_id = block_id

        logger.info(
            "%s blocked %d pages into %d blocks",
            type(self).__name__,
            len(pages),
            len(blocks),
        )
        return BlockerResult(blocks=blocks)

    def _block_page(self, page: Image, page_index: int) -> list[Block]:
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
