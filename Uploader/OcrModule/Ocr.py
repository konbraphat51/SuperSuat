from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

@dataclass
class OcrResultBlock:
    block_type: Literal["text", "image", "table", "equation", "footer", "section"]

class OcrResultBlockText(OcrResultBlock):
    text: str

class OcrResultBlockImage(OcrResultBlock):
    image_data: bytes
    caption: str

class OcrResultBlockTable(OcrResultBlock):
    text: str # in Markdown format
    caption: str

class OcrResultBlockEquation(OcrResultBlock):
    text: str # in LaTeX format
    caption: str

class OcrResultBlockFooter(OcrResultBlock):
    text: str

class OcrResultBlockSection(OcrResultBlock):
    text: str
    level: int

class OcrResult:
    blocks: list[OcrResultBlock]

class Ocr(ABC):
    @abstractmethod
    def ocr(
        self,
        image_data: list[bytes],
    ) -> OcrResult:
        pass
