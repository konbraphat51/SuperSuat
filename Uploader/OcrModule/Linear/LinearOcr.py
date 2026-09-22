"""Reading a document one page at a time, front to back."""

from PIL.Image import Image
from langchain_core.language_models import BaseChatModel
from tqdm import tqdm
from ..Ocr import Ocr
from ..OcrSchema import OcrResultSection, OcrResult
from ..LlmHelper import ImageBase64, pil_to_base64
from .OcrAgent import OcrAgent
from .OcrDataEditor import OcrDataEditor


class LinearOcr(Ocr):
    """Reads each page in turn, growing one document tree as it goes.

    Every page is one OcrAgent run, whose reported operations OcrDataEditor
    applies before the next page is read - so each page is written against
    the structure the pages before it produced."""

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
        """Reads every page, in order, into a single document tree."""
        # converted up front so no PIL.Image.Image is held onto beyond here
        all_pages = [
            ImageBase64(b64=pil_to_base64(img), size=img.size)
            for img in all_page_images
        ]

        self._initialize_entire_section()
        ocr_agent = OcrAgent(
            ocr_model=self.ocr_model,
            clipper_model=self.clipper_model,
            all_pages=all_pages,
            entire_section=self.entire_section,
        )
        editor = OcrDataEditor(self.entire_section)

        # a page is slow enough (several model calls) that showing which one
        # is in flight is what makes it obvious the process is alive
        page_progress = tqdm(range(len(all_pages)), desc="OCR", unit="page")
        for page_number in page_progress:
            page_progress.set_description(
                f"OCR (page {page_number + 1}/{len(all_pages)})"
            )
            output = ocr_agent.read_page(page_number)
            editor.apply(output, page_number)

        return OcrResult(root_section=self.entire_section)

    def _initialize_entire_section(self) -> None:
        self.entire_section = OcrResultSection(
            block_type="section",
            existing_pages=[],
            block_index=0,
            section_content=[],
        )
