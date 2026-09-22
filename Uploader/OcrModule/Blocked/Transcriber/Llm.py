from PIL.Image import Image
from langchain_core.language_models import BaseChatModel
from ..Schema import (
    BlockType,
    BlockerResult,
    Block,
    TranscriptionBlock,
    TranscriptionResult,
)
from ...LlmHelper import (
    pil_to_base64,
)
from .Transcriber import Transcriber

class LlmTranscriber(Transcriber):
    def __init__(
        self,
        ocr_model: BaseChatModel,
    ) -> None:
        self.ocr_model = ocr_model

    def _ocr_block_image(
        self,
        block_image: Image,
    ) -> str:
        # convert image data
        image_base64 = pil_to_base64(block_image)
