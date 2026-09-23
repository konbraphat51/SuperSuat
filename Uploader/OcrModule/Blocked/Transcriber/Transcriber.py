"""Abstract base for the transcription stage of the OCR pipeline."""

from abc import ABC, abstractmethod
from collections import defaultdict
from PIL.Image import Image
from ..PageParallel import DEFAULT_MAX_PARALLEL_PAGES, map_pages
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
    are left for later pipeline stages and are not transcribed here.

    A page's blocks are read one after another, but several pages are read at
    the same time. A subclass whose model does not take being called from
    several threads at once lowers MAX_PARALLEL_PAGES."""

    # Pages read at once. Lower it in a subclass whose model cannot take it.
    MAX_PARALLEL_PAGES = DEFAULT_MAX_PARALLEL_PAGES

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
        blocks_by_page = self._group_text_blocks_by_page(blocker_result)

        pages_transcriptions = map_pages(
            lambda page: self._transcribe_page(all_pages[page[0]], page[1]),
            list(blocks_by_page.items()),
            self.MAX_PARALLEL_PAGES,
        )

        return TranscriptionResult(
            [
                transcription
                for page_transcriptions in pages_transcriptions
                for transcription in page_transcriptions
            ]
        )

    def _group_text_blocks_by_page(
        self,
        blocker_result: BlockerResult,
    ) -> dict[int, list[Block]]:
        """The TEXT blocks of each page, keyed by page, both in block order.

        Non-TEXT blocks (MATH, IMAGE, TABLE) are left for later pipeline
        stages, so they are dropped here rather than read.
        """
        blocks_by_page: dict[int, list[Block]] = defaultdict(list)

        for block in blocker_result.blocks:
            if block.block_type != BlockType.TEXT:
                continue

            blocks_by_page[block.page_index].append(block)

        return blocks_by_page

    def _transcribe_page(
        self,
        page: Image,
        blocks: list[Block],
    ) -> list[TranscriptionBlock]:
        """Transcribes one page's blocks, one after another, in block order."""
        transcriptions: list[TranscriptionBlock] = []

        # for each block...
        for block in blocks:
            # ...OCR the block

            # image extraction
            block_image = self._extract_block_image(page, block)

            # transcribe the block image
            text = self._ocr_text_block_image(block_image)
            transcriptions.append(
                TranscriptionBlock(block_id=block.block_id, text=text)
            )

        return transcriptions

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
