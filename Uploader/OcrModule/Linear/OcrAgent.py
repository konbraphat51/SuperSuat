from langchain_core.language_models import BaseChatModel
from .Tools import LinearTools

class OcrAgent:
    def __init__(
        self,
        ocr_model: BaseChatModel,
        linear_tools: LinearTools
    ) -> None:
        self.ocr_model = ocr_model
        self.linear_tools = linear_tools

    def read_page(
        self,
        page_number: int,
    ) -> None:
        raise NotImplementedError("The read_page method is not implemented yet. Please implement this method to perform OCR on the specified page number.")