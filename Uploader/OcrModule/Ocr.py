from abc import ABC, abstractmethod
from PIL.Image import Image

from OcrModule.OcrSchema import OcrResult


class Ocr(ABC):
    @abstractmethod
    def ocr(
        self,
        image_data: list[Image],
    ) -> OcrResult:
        pass
