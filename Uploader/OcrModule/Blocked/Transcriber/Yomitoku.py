"""Text transcription backed by yomitoku's text recognition model."""

import logging

import numpy as np
import torch
from PIL.Image import Image
from yomitoku import TableStructureRecognizer, TextDetector, TextRecognizer
from yomitoku.document_analyzer import extract_words_within_element
from yomitoku.export.export_markdown import table_to_md
from yomitoku.ocr import ocr_aggregate
from yomitoku.schemas import OCRSchema

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
        self._detector = TextDetector(device=self._device, visualize=visualize)
        self._table_structure_recognizer = TableStructureRecognizer(
            device=self._device,
            visualize=visualize,
        )
        logger.info("YomitokuTranscriber ready on device=%s", self._device)

    @staticmethod
    def default_device() -> str:
        """ "cuda" whenever this machine can run the model on the GPU."""
        return "cuda" if torch.cuda.is_available() else "cpu"

    def _ocr_text_block_image(self, block_image: Image) -> str:
        """Returns the transcribed text of the block image."""
        results, _ = self._recognizer(self._to_bgr_array(block_image))
        return "".join(results.contents)

    def _ocr_table_block_image(self, block_image: Image) -> str:
        """Returns the transcribed Markdown table of the table block image."""
        image = self._to_bgr_array(block_image)
        height, width = image.shape[:2]

        # detect and recognize every word in the table
        detection, _ = self._detector(image)
        recognition, _ = self._recognizer(image, detection.points)
        words = OCRSchema(words=ocr_aggregate(detection, recognition)).words

        # recognize the table structure, treating the whole crop as one table
        tables, _ = self._table_structure_recognizer(image, [[0, 0, width, height]])
        if not tables:
            return ""
        table = tables[0]

        # assign each cell its contained words
        for cell in table.cells:
            contents, _, _ = extract_words_within_element(words, cell)
            cell.contents = contents or ""

        return table_to_md(table, ignore_line_break=False)["md"].strip()

    @staticmethod
    def _to_bgr_array(image: Image) -> np.ndarray:
        """The image as the contiguous OpenCV-style BGR array yomitoku expects."""
        return np.ascontiguousarray(np.array(image.convert("RGB"))[:, :, ::-1])
