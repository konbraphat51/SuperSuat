"""Text transcription backed by yomitoku's text recognition model."""

import logging

import numpy as np
import torch
from PIL.Image import Image
from yomitoku import TextRecognizer

from .Transcriber import Transcriber

logger = logging.getLogger(__name__)


class YomitokuTranscriber(Transcriber):
    """Reads block text with yomitoku's text recognizer.

    Only the recognition stage of yomitoku is used: each block image is
    already an isolated crop, so no text detection is needed before
    recognition runs on it."""

    def __init__(
        self,
        device: str | None = None,
        model_name: str = "parseq-middle-dynw-v5",
        visualize: bool = False,
    ) -> None:
        """Loads the recognition model onto `device`, or onto the best one available.

        Args:
            device: Torch device the model runs on, e.g. "cuda" or "cpu".
            model_name: Name of the yomitoku text recognition model to use.
            visualize: Whether yomitoku renders its debug overlays.
        """
        self._device = device or self.default_device()
        self._recognizer = TextRecognizer(
            model_name=model_name,
            device=self._device,
            visualize=visualize,
        )
        logger.info("YomitokuTranscriber ready on device=%s", self._device)

    @staticmethod
    def default_device() -> str:
        """ "cuda" whenever this machine can run the model on the GPU."""
        return "cuda" if torch.cuda.is_available() else "cpu"

    def _ocr_block_image(self, block_image: Image) -> str:
        """Returns the transcribed text of the block image."""
        results, _ = self._recognizer(self._to_bgr_array(block_image))
        return "".join(results.contents)

    @staticmethod
    def _to_bgr_array(image: Image) -> np.ndarray:
        """The image as the contiguous OpenCV-style BGR array yomitoku expects."""
        return np.ascontiguousarray(np.array(image.convert("RGB"))[:, :, ::-1])
