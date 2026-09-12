from PIL.Image import Image
from langchain_core.language_models import BaseChatModel
from ..Ocr import Ocr
from ..OcrSchema import OcrResultSection, OcrResult
from .OcrAgent import OcrAgent

class LinearOcr(Ocr):
    def __init__(
        self,
        ocr_model: BaseChatModel,
        clipper_model: BaseChatModel,
    ) -> None:
        self.ocr_model = ocr_model
        self.clipper_model = clipper_model
        self.entire_section: OcrResultSection

    def ocr(
         self,
         all_page_images: list[Image],
     ) -> OcrResult:
         # Implement the OCR logic here
        self.all_page_images = all_page_images
        self._initialize_entire_section()
        ocr_agent = OcrAgent(
            ocr_model=self.ocr_model,
            clipper_model=self.clipper_model,
            all_page_images=self.all_page_images,
            entire_section=self.entire_section,
        )

        for page_number in range(len(all_page_images)):
            ocr_agent.read_page(page_number)

        return OcrResult(root_section=self.entire_section)


    def _initialize_entire_section(self) -> None:
        self.entire_section = OcrResultSection(
            section_content=[],
            section_index=0,
            existing_pages=[],
        )
