from PIL.Image import Image
from langchain_core.language_models import BaseChatModel
from tqdm import tqdm
from ..Ocr import Ocr
from ..OcrSchema import OcrResultSection, OcrResult
from ..LlmHelper import (
    ImageBase64,
    ImageMessageBuilder,
    build_image_message_openai,
    pil_to_base64,
)
from .OcrAgent import OcrAgent
from .OcrDataEditor import OcrDataEditor


class LinearOcr(Ocr):
    def __init__(
        self,
        ocr_model: BaseChatModel,
        clipper_model: BaseChatModel,
        image_message_builder: ImageMessageBuilder = build_image_message_openai,
        clipper_image_message_builder: ImageMessageBuilder | None = None,
    ) -> None:
        self.ocr_model = ocr_model
        self.clipper_model = clipper_model
        self.image_message_builder = image_message_builder
        self.clipper_image_message_builder = clipper_image_message_builder
        self.entire_section: OcrResultSection

    def ocr(
        self,
        all_page_images: list[Image],
    ) -> OcrResult:
        # Convert every page to base64 up front so no PIL.Image.Image is held
        # onto beyond this point.
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
            image_message_builder=self.image_message_builder,
            clipper_image_message_builder=self.clipper_image_message_builder,
        )
        editor = OcrDataEditor(self.entire_section)

        # Pages can each take a while (multiple LLM/tool round-trips), so a
        # progress bar showing which page is in flight makes it obvious the
        # process is alive and roughly how far through the document it is.
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
