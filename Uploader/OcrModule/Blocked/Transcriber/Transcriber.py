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
    def transcribe(
        self,
        all_pages: list[Image],
        blocker_result: BlockerResult,
    ) -> TranscriptionResult:
        transcriptions: list[TranscriptionBlock] = []
        
        # for each block...
        for block in blocker_result.blocks:
            # ...OCR the block

            # skip if the block is not text
            if block.block_type != BlockType.TEXT:
                continue

            # image extraction
            block_image = self._extract_block_image(all_pages[block.page_number], block)

            # transcribe the block image
            text = self._ocr_block_image(block_image)
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
    def _ocr_block_image(
        self,
        block_image: Image,
    ) -> str:
        """Returns the transcribed text of the block image."""
        raise NotImplementedError("Subclasses must implement this method.")
