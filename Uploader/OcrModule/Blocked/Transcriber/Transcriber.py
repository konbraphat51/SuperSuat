"""Abstract base for the transcription stage of the OCR pipeline."""

from abc import ABC, abstractmethod
from PIL.Image import Image
from ..Schema import (
    BlockType,
    BlockerResult,
    Block,
    TranscriptionBlock,
    TranscriptionResult,
)


class Transcriber(ABC):
    """Reads the text of each TEXT block found by a Blocker.

    Blocks are OCR'd one at a time, in isolation, so each recognition call
    sees only the text it needs to read. Non-TEXT blocks (MATH, IMAGE, TABLE)
    are left for later pipeline stages and are not transcribed here."""

    def transcribe(
        self,
        all_pages: list[Image],
        blocker_result: BlockerResult,
    ) -> TranscriptionResult:
        """Transcribes every TEXT block of blocker_result, cropped from all_pages.

        Args:
            all_pages: Every page image, indexed by Block.page_index.
            blocker_result: The blocks detected by a Blocker, to be transcribed.
        """
        transcriptions: list[TranscriptionBlock] = []

        # for each block...
        for block in blocker_result.blocks:
            # ...OCR the block

            # skip if the block is not text
            if block.block_type != BlockType.TEXT:
                continue

            # image extraction
            block_image = self._extract_block_image(all_pages[block.page_index], block)

            # transcribe the block image
            text = self._ocr_text_block_image(block_image)
            transcriptions.append(TranscriptionBlock(block, text))

        return TranscriptionResult(transcriptions)

    def _extract_block_image(
        self,
        page: Image,
        block: Block,
    ) -> Image:
        """Returns a cropped copy of the page image, containing only the block."""
        x, y, width, height = block.bounding_box
        return page.crop((x, y, x + width, y + height))

    @abstractmethod
    def _ocr_text_block_image(
        self,
        block_image: Image,
    ) -> str:
        """Returns the transcribed text of the text block image."""
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def _ocr_table_block_image(
        self,
        block_image: Image,
    ) -> str:
        """Returns the transcribed text of the table block image."""
        raise NotImplementedError("Subclasses must implement this method.")
