"""Text transcription backed by a general-purpose multimodal LLM."""

from PIL.Image import Image
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from ...LlmHelper import (
    build_image_message,
    pil_to_base64,
    stringify_message_content,
)
from .Transcriber import Transcriber

PROMPT = """You are a highly precise OCR engine. Transcribe every character visible in the given image exactly as it is written.

Rules:
- Output only the transcription itself: no preamble, no explanation, no surrounding quotes or code fences.
- Write the transcription in Markdown, using Markdown syntax (headings, lists, bold/italic, tables, etc.) only where the image's own formatting clearly calls for it.
- Write every mathematical expression in KaTeX-compatible LaTeX: `$...$` for inline math and `$$...$$` for display/block equations.
- Keep the transcription in the same language as the text in the image. Never translate, paraphrase, or summarize.
- Reproduce the text verbatim, including punctuation, casing, numbers, and line breaks that carry meaning (e.g. list items, paragraph breaks).
- Do not invent, complete, or correct text that is unclear or cut off; transcribe only what is actually visible.
- If the image contains no legible text, output nothing.
"""


class LlmTranscriber(Transcriber):
    """Reads block text by asking a multimodal chat model to transcribe the
    cropped block image, following PROMPT's OCR instructions."""

    def __init__(
        self,
        ocr_model: BaseChatModel,
    ) -> None:
        """
        Args:
            ocr_model: Multimodal chat model used to transcribe block images.
        """
        self.ocr_model = ocr_model

    def _ocr_block_image(
        self,
        block_image: Image,
    ) -> str:
        """Returns the transcribed text of the block image."""
        # convert image data
        image_base64 = pil_to_base64(block_image)

        # get transcription from LLM
        return self._send_to_llm(image_base64)

    def _send_to_llm(
        self,
        image_base64: str,
    ) -> str:
        """Image -> transcription"""
        message = HumanMessage(content=build_image_message(PROMPT, image_base64))
        result = self.ocr_model.invoke([message])
        return stringify_message_content(result.content).strip()
