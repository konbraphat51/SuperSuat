"""Block detection backed by PP-StructureV3's layout detection model."""

import logging

import numpy as np

# Paddle puts its own DLL directory first on Windows, which then shadows the
# ones torch needs: torch has to be imported before paddle, or every later
# `import torch` in the process fails.
import torch  # noqa: F401
import paddle
from paddleocr import LayoutDetection
from PIL.Image import Image

from .Blocker import Blocker
from ..Schema import Block, BlockerResult, BlockType

logger = logging.getLogger(__name__)

# The layout model PP-StructureV3 uses by default. Lighter variants
# (PP-DocLayout-L / -M / -S) can be passed as `model_name`.
DEFAULT_MODEL_NAME = "PP-DocLayout_plus-L"

# The twenty labels the PP-DocLayout models emit. Everything that is read as
# prose stays TEXT, including captions, headers, footers, and page numbers.
LABEL_BLOCK_TYPES = {
    "paragraph_title": BlockType.TEXT,
    "image": BlockType.IMAGE,
    "text": BlockType.TEXT,
    "number": BlockType.TEXT,
    "abstract": BlockType.TEXT,
    "content": BlockType.TEXT,
    "figure_title": BlockType.TEXT,
    "formula": BlockType.MATH,
    "table": BlockType.TABLE,
    "reference": BlockType.TEXT,
    "doc_title": BlockType.TEXT,
    "footnote": BlockType.TEXT,
    "header": BlockType.TEXT,
    "algorithm": BlockType.TEXT,
    "footer": BlockType.TEXT,
    "seal": BlockType.IMAGE,
    "chart": BlockType.IMAGE,
    "formula_number": BlockType.TEXT,
    "aside_text": BlockType.TEXT,
    "reference_content": BlockType.TEXT,
}


class PpStructureBlocker(Blocker):
    """Splits page images into blocks with PP-StructureV3's layout model.

    Only the layout stage of PP-StructureV3 is used: its OCR, table, and
    formula recognizers would read the text that step 2 reads anyway, block by
    block, so they are left out."""

    def __init__(
        self,
        device: str | None = None,
        model_name: str = DEFAULT_MODEL_NAME,
        model_dir: str | None = None,
        threshold: float | None = None,
    ) -> None:
        """Loads the layout model onto `device`, or onto the best one available.

        Args:
            device: Paddle device the model runs on, e.g. "gpu" or "cpu".
            model_name: Layout model to run, from the PP-DocLayout family.
            model_dir: Local model directory to use instead of the released one.
            threshold: Lowest detection score kept; the model default if None.
        """
        self._device = device or self.default_device()
        self._detector = LayoutDetection(
            model_name=model_name,
            model_dir=model_dir,
            threshold=threshold,
            device=self._device,
        )
        logger.info(
            "PpStructureBlocker ready on device=%s with model=%s",
            self._device,
            model_name,
        )

    @staticmethod
    def default_device() -> str:
        """ "gpu" whenever this machine can run the model on the GPU."""
        return "gpu" if paddle.device.cuda.device_count() > 0 else "cpu"

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
        detection = self._detector.predict(self._to_bgr_array(page))[0]

        blocks = [
            Block(
                block_type=self._label_block_type(box["label"]),
                page_number=page_number,
                bounding_box=self._to_bounding_box(box["coordinate"]),
            )
            for box in detection["boxes"]
        ]
        blocks.sort(key=lambda block: (block.bounding_box[1], block.bounding_box[0]))
        return blocks

    @staticmethod
    def _label_block_type(label: str) -> BlockType:
        """The BlockType a PP-DocLayout label maps to, defaulting to TEXT."""
        return LABEL_BLOCK_TYPES.get(label, BlockType.TEXT)

    @staticmethod
    def _to_bgr_array(page: Image) -> np.ndarray:
        """The page as the contiguous OpenCV-style BGR array PaddleX expects."""
        return np.ascontiguousarray(np.array(page.convert("RGB"))[:, :, ::-1])

    @staticmethod
    def _to_bounding_box(coordinate: np.ndarray) -> tuple[int, int, int, int]:
        """A PaddleX [x1, y1, x2, y2] box as Block's (x, y, width, height)."""
        x1, y1, x2, y2 = (int(round(float(value))) for value in coordinate)
        return (x1, y1, x2 - x1, y2 - y1)
