import base64
from io import BytesIO
from PIL.Image import Image
from langchain_core.language_models import BaseChatModel
from ..Ocr import Ocr
from ..OcrSchema import OcrResultSection, OcrResult
from .OcrAgent import OcrAgent

def pil_to_base64(img: Image, format: str = "PNG") -> str:
    buffered = BytesIO()
    img.save(buffered, format=format)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

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
        # Convert every page to base64 up front so no PIL.Image.Image is held
        # onto beyond this point.
        all_page_b64 = [pil_to_base64(img) for img in all_page_images]
        all_page_sizes = [img.size for img in all_page_images]

        self._initialize_entire_section()
        ocr_agent = OcrAgent(
            ocr_model=self.ocr_model,
            clipper_model=self.clipper_model,
            all_page_b64=all_page_b64,
            all_page_sizes=all_page_sizes,
            entire_section=self.entire_section,
        )

        for page_number in range(len(all_page_b64)):
            ocr_agent.read_page(page_number)

        return OcrResult(root_section=self.entire_section)


    def _initialize_entire_section(self) -> None:
        self.entire_section = OcrResultSection(
            block_type="section",
            existing_pages=[],
            block_index=0,
            section_content=[],
        )
