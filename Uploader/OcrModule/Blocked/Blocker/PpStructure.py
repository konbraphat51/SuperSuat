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

logger = logging.getLogger(__name__)

# The layout model PP-StructureV3 uses by default. Lighter variants
# (PP-DocLayout-L / -M / -S) can be passed as `model_name`.
DEFAULT_MODEL_NAME = "PP-DocLayout_plus-L"


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

    def _detect_page(self, page: Image) -> list[tuple[int, int, int, int]]:
        """The bounding boxes PP-DocLayout detects in the page."""
        detection = self._detector.predict(self._to_bgr_array(page))[0]

        # the detected label is dropped: the Classifier reads what the block
        # is off the page, from categories this detector does not have
        return [self._to_bounding_box(box["coordinate"]) for box in detection["boxes"]]

    @staticmethod
    def _to_bgr_array(page: Image) -> np.ndarray:
        """The page as the contiguous OpenCV-style BGR array PaddleX expects."""
        return np.ascontiguousarray(np.array(page.convert("RGB"))[:, :, ::-1])

    @staticmethod
    def _to_bounding_box(coordinate: np.ndarray) -> tuple[int, int, int, int]:
        """A PaddleX [x1, y1, x2, y2] box as Block's (x, y, width, height)."""
        x1, y1, x2, y2 = (int(round(float(value))) for value in coordinate)
        return (x1, y1, x2 - x1, y2 - y1)
