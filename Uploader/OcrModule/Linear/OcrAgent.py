from PIL.Image import Image
from langchain_core.language_models import BaseChatModel
from .Tools import LinearTools
from ..OcrSchema import OcrResultSection

class OcrAgent:
    def __init__(
        self,
        ocr_model: BaseChatModel,
        linear_tools: LinearTools,
        all_page_images: list[Image],
        entire_section: OcrResultSection
    ) -> None:
        self.ocr_model = ocr_model
        self.linear_tools = linear_tools
        self.all_page_images = all_page_images
        self.entire_section = entire_section

    def read_page(
        self,
        page_number: int,
    ) -> None:
        raise NotImplementedError("The read_page method is not implemented yet. Please implement this method to perform OCR on the specified page number.")