"""Block detection backed by yomitoku's layout analysis models."""

import logging
from collections.abc import Sequence

import numpy as np
import torch
from PIL.Image import Image
from yomitoku import LayoutAnalyzer

from .Blocker import Blocker
from ..Schema import BlockType

logger = logging.getLogger(__name__)

# Paragraph roles that mean the block is a formula rather than prose. Only the
# layout models trained with a formula category emit these.
FORMULA_ROLES = {
    "inline_formula": BlockType.MATH,
    "display_formula": BlockType.MATH,
}


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

    def _detect_page(
        self, page: Image
    ) -> list[tuple[BlockType, tuple[int, int, int, int]]]:
        """The (block type, bounding box) pairs yomitoku detects in the page."""
        layout, _ = self._analyzer(self._to_bgr_array(page))

        elements: list[tuple[Sequence[int], BlockType]] = [
            *(
                (paragraph.box, self._paragraph_block_type(paragraph.role))
                for paragraph in layout.paragraphs
            ),
            *((figure.box, BlockType.IMAGE) for figure in layout.figures),
            *((table.box, BlockType.TABLE) for table in layout.tables),
        ]

        return [
            (block_type, self._to_bounding_box(box)) for box, block_type in elements
        ]

    @staticmethod
    def _paragraph_block_type(role: str | None) -> BlockType:
        """MATH for a paragraph the layout model marked as a formula, else TEXT."""
        return FORMULA_ROLES.get(role, BlockType.TEXT)

    @staticmethod
    def _to_bgr_array(page: Image) -> np.ndarray:
        """The page as the contiguous OpenCV-style BGR array yomitoku expects."""
        return np.ascontiguousarray(np.array(page.convert("RGB"))[:, :, ::-1])

    @staticmethod
    def _to_bounding_box(box: Sequence[int]) -> tuple[int, int, int, int]:
        """A yomitoku [x1, y1, x2, y2] box as Block's (x, y, width, height)."""
        x1, y1, x2, y2 = box
        return (x1, y1, x2 - x1, y2 - y1)
