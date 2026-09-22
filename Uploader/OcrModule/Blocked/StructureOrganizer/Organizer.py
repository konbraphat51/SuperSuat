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


class Organizer:
    def __init__(
        self,
        organizer_model: BaseChatModel,
    ) -> None:
        self.organizer_model = organizer_model

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
        for page_number in range(len(all_page_images)):
            # ... scan this page
            raise NotImplementedError("Organizer.organize() is not yet implemented.")

        # TODO: convert to OcrResult
        raise NotImplementedError("Organizer.organize() is not yet implemented.")

    def _scan_page(
        self,
        page_number: int,  # 1-indexed
        page_image: Image,
        page_image_rendered: Image,
        page_images_former: list[Image],
        processing_blocks: list[ProcessingBlock],
    ) -> None:
        pass
