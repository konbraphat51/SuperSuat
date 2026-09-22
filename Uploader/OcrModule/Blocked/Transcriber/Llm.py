from PIL.Image import Image
from langchain_core.language_models import BaseChatModel
from ..Schema import (
    BlockType,
    BlockerResult,
    Block,
    TranscriptionBlock,
    TranscriptionResult,
)
from .Transcriber import Transcriber

class LlmTranscriber(Transcriber):
    def __init__(
        self,
        ocr_model: BaseChatModel,
    ) -> None:
        self.ocr_model = ocr_model
