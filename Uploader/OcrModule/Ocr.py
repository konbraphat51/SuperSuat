"""The interface every OCR implementation provides."""

from abc import ABC, abstractmethod
from PIL.Image import Image

from OcrModule.OcrSchema import OcrResult


class Ocr(ABC):
    """Turns the page images of one document into a structured OcrResult."""

    @abstractmethod
    def ocr(
        self,
        all_page_images: list[Image],
    ) -> OcrResult:
        """Reads every page, in order, into a single document tree."""
        pass
