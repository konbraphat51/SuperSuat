from PIL.Image import Image
from langchain_core.language_models import BaseChatModel
from ...OcrSchema import OcrResult
from ..Schema import (
    BlockerResult,
    Block,
    TranscriptionResult,
)
from .ProcessingSchema import (
    ProcessingBlock,
    ProcessingBlockText,
    ProcessingBlockTextHeading,
    ProcessingBlockFigure,
    convert_blocker_result_to_processing_blocks,
)

from .OrganizerAgent import OrganizerAgent
from .DataExporter import export_processing_blocks_to_ocr_result


class Organizer:
    def __init__(
        self,
        organizer_model: BaseChatModel,
    ) -> None:
        self.organizer_agent = OrganizerAgent(organizer_model=organizer_model)

    def organize(
        self,
        all_page_images: list[Image],
        all_page_images_rendered: list[Image],
        blocker_result: BlockerResult,
        transcription_result: TranscriptionResult,
    ) -> OcrResult:
        # convert data
        processing_blocks = convert_blocker_result_to_processing_blocks(
            blocker_result=blocker_result,
            transcription_result=transcription_result,
        )

        # for all pages...
        for page_index in range(len(all_page_images)):
            # ... scan this page
            self._scan_page(
                page_index=page_index,
                all_page_images=all_page_images,
                page_image_rendered=all_page_images_rendered[page_index],
                processing_blocks=processing_blocks,
            )

        # build the document tree out of the settled blocks
        return export_processing_blocks_to_ocr_result(processing_blocks)

    def _scan_page(
        self,
        page_index: int,
        all_page_images: list[Image],
        page_image_rendered: Image,
        processing_blocks: list[ProcessingBlock],
    ) -> None:
        self.organizer_agent.scan_page(
            page_index=page_index,
            all_page_images=all_page_images,
            page_image_rendered=page_image_rendered,
            processing_blocks=processing_blocks,
        )
