from PIL.Image import Image
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import tool
from ..Ocr import Ocr
from ..OcrSchema import OcrResultSection, OcrResult
from .Tools import LinearTools
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
        self._initialize_tools()
        ocr_agent = OcrAgent(self.ocr_model, self.linear_tools)

        for page_number in range(len(all_page_images)):
            ocr_agent.read_page(page_number)

        return OcrResult(root_section=self.entire_section)


    def _initialize_entire_section(self) -> None:
        self.entire_section = OcrResultSection(
            section_content=[],
            section_index=0,
            existing_pages=[],
        )

    def _initialize_tools(self) -> None:
        self.linear_tools = LinearTools(
            all_page_images=self.all_page_images,
            ocr_entire_section=self.entire_section,
            clipper_model=self.clipper_model,
        )

        self.tools = [
            tool(self.linear_tools.set_current_page),
            tool(self.linear_tools.get_page_image),
            tool(self.linear_tools.edit_block),
            tool(self.linear_tools.add_text_block),
            tool(self.linear_tools.add_image_block),
            tool(self.linear_tools.add_section),
            tool(self.linear_tools.move_block),
            tool(self.linear_tools.clip_image),
        ]
