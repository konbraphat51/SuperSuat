"""Block detection backed by yomitoku's layout analysis models."""

import logging
from collections.abc import Sequence

import numpy as np
import torch
from PIL.Image import Image
from yomitoku import LayoutAnalyzer

from .Blocker import Blocker
from ..Schema import Block, BlockerResult, BlockType

logger = logging.getLogger(__name__)


class YomitokuBlocker(Blocker):
    """Splits page images into blocks with yomitoku's layout analyzer.

    Only the layout stage of yomitoku is used: the text of each block is read
    later, by the OCR step, so that every block can be recognized in
    isolation."""

    def __init__(
        self,
        device: str | None = None,
        configs: dict | None = None,
        visualize: bool = False,
    ) -> None:
        """Loads the layout models onto `device`, or onto the best one available.

        Args:
            device: Torch device the models run on, e.g. "cuda" or "cpu".
            configs: Per-model yomitoku overrides, keyed by model name.
            visualize: Whether yomitoku renders its debug overlays.
        """
        self._device = device or self.default_device()
        self._analyzer = LayoutAnalyzer(
            configs=configs or {},
            device=self._device,
            visualize=visualize,
        )
        logger.info("YomitokuBlocker ready on device=%s", self._device)

    @staticmethod
    def default_device() -> str:
        """ "cuda" whenever this machine can run the models on the GPU."""
        return "cuda" if torch.cuda.is_available() else "cpu"

    def block(
        self,
        pages: list[Image],
    ) -> BlockerResult:
        """Detects blocks of text, math, images, and tables in the page images."""
        blocks: list[Block] = []
        for page_number, page in enumerate(pages):
            blocks.extend(self._block_page(page, page_number))

        logger.info("blocked %d pages into %d blocks", len(pages), len(blocks))
        return BlockerResult(blocks=blocks)

    def _block_page(self, page: Image, page_number: int) -> list[Block]:
        """Every block of one page, ordered top-to-bottom then left-to-right.

        The page number is 0-indexed, as elsewhere in the OCR module."""
        layout, _ = self._analyzer(self._to_bgr_array(page))

        # yomitoku's layout model knows nothing of formulas: a block holding one
        # is reported as text here, and the LLM step tells the two apart.
        elements: list[tuple[Sequence[int], BlockType]] = [
            *((paragraph.box, BlockType.TEXT) for paragraph in layout.paragraphs),
            *((figure.box, BlockType.IMAGE) for figure in layout.figures),
            *((table.box, BlockType.TABLE) for table in layout.tables),
        ]

        blocks = [
            Block(
                block_type=block_type,
                page_number=page_number,
                bounding_box=self._to_bounding_box(box),
            )
            for box, block_type in elements
        ]
        blocks.sort(key=lambda block: (block.bounding_box[1], block.bounding_box[0]))
        return blocks

    @staticmethod
    def _to_bgr_array(page: Image) -> np.ndarray:
        """The page as the contiguous OpenCV-style BGR array yomitoku expects."""
        return np.ascontiguousarray(np.array(page.convert("RGB"))[:, :, ::-1])

    @staticmethod
    def _to_bounding_box(box: Sequence[int]) -> tuple[int, int, int, int]:
        """A yomitoku [x1, y1, x2, y2] box as Block's (x, y, width, height)."""
        x1, y1, x2, y2 = box
        return (x1, y1, x2 - x1, y2 - y1)
