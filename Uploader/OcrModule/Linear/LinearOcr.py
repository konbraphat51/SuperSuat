from PIL.Image import Image
from langchain_core.language_models import BaseChatModel
from ..Ocr import Ocr

class LinearOcr(Ocr):
    def __init__(
        self,
        ocr_model: BaseChatModel,
    ) -> None:
        self.ocr_model = ocr_model

    def ocr(
         self,
         all_page_images: list[Image],
     ) -> OcrResult:
         # Implement the OCR logic here
         pass