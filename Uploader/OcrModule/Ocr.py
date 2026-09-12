from abc import ABC, abstractmethod
from PIL.Image import Image

from OcrModule.OcrSchema import OcrResult


class Ocr(ABC):
    @abstractmethod
    def ocr(
        self,
        all_page_images: list[Image],
    ) -> OcrResult:
        pass
