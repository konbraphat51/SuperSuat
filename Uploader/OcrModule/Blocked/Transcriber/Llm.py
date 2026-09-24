"""Text transcription backed by a general-purpose multimodal LLM."""

from PIL.Image import Image
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from ...LlmHelper import (
    build_image_message,
    pil_to_base64,
    stringify_message_content,
    strip_code_fence,
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

TABLE_PROMPT = """You are a highly precise OCR engine. Transcribe the table in the given image into a single Markdown table.

Rules:
- Output only the Markdown table itself: no preamble, no explanation, no surrounding quotes or code fences.
- Reproduce the table's row and column structure exactly as shown, including header rows.
- For merged cells, repeat the same content in every cell the merge spans.
- Write every mathematical expression in KaTeX-compatible LaTeX: `$...$` for inline math and `$$...$$` for display/block equations.
- Keep the transcription in the same language as the text in the image. Never translate, paraphrase, or summarize.
- Reproduce text verbatim, including punctuation, casing, and numbers.
- Do not invent, complete, or correct text that is unclear or cut off; transcribe only what is actually visible.
- If a cell is empty in the image, leave it empty in the output.
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

    def _ocr_text_block_image(
        self,
        block_image: Image,
    ) -> str:
        """Returns the transcribed text of the block image."""
        # convert image data
        image_base64 = pil_to_base64(block_image)

        # get transcription from LLM
        return self._send_to_llm(image_base64, PROMPT)

    def _ocr_table_block_image(
        self,
        block_image: Image,
    ) -> str:
        """Returns the transcribed Markdown table of the table block image."""
        # convert image data
        image_base64 = pil_to_base64(block_image)

        # get transcription from LLM
        return self._send_to_llm(image_base64, TABLE_PROMPT)

    def _send_to_llm(
        self,
        image_base64: str,
        prompt: str,
    ) -> str:
        """Image -> transcription"""
        message = HumanMessage(content=build_image_message(prompt, image_base64))
        result = self.ocr_model.invoke([message])
        return strip_code_fence(stringify_message_content(result.content).strip())
