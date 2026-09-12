from PIL.Image import Image
from langchain_core.language_models import BaseChatModel
from ..Ocr import Ocr
from ..OcrSchema import OcrResultSection

class LinearOcr(Ocr):
    def __init__(
        self,
        ocr_model: BaseChatModel,
    ) -> None:
        self.ocr_model = ocr_model
        self.entire_section: OcrResultSection

    def ocr(
         self,
         all_page_images: list[Image],
     ) -> OcrResult:
         # Implement the OCR logic here
        self._initialize_entire_section()

    def _initialize_entire_section(self) -> None:
        self.entire_section = OcrResultSection(
            section_content=[],
            section_index=0,
            existing_pages=[],
        )
