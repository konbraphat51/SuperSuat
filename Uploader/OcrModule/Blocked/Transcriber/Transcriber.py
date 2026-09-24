"""Abstract base for the transcription stage of the OCR pipeline."""

from abc import ABC, abstractmethod

from PIL.Image import Image

from ..PageParallel import DEFAULT_MAX_PARALLEL_PAGES, run_parallel
from ..Schema import (
    TranscriptionBlock,
    TranscriptionResult,
    TranscriptionTarget,
    TranscriptionType,
)

# Pixels added on every side of a block before it is cropped. A box that sits
# a hair inside the ink cuts the top off a line, and a few pixels of the page
# around a block cost the recognizer nothing.
BLOCK_CROP_PADDING = 4


class Transcriber(ABC):
    """Reads the text of each block the Classifier said holds text.

    Blocks are OCR'd one at a time, in isolation, so each recognition call
    sees only the text it needs to read - and, since this runs after the
    Classifier, it knows what kind of thing it is reading: a table is read as
    a whole, into a Markdown table, and everything else as running text. A
    figure is not read at all; what a figure says is in the picture.

    Blocks are independent, so MAX_PARALLEL_BLOCKS of them are read at once. A
    subclass whose model does not take being called from several threads at
    once lowers that to 1."""

    # Blocks read at once. Lower it in a subclass whose model cannot take it.
    MAX_PARALLEL_BLOCKS = DEFAULT_MAX_PARALLEL_PAGES

    def transcribe(
        self,
        all_pages: list[Image],
        targets: list[TranscriptionTarget],
    ) -> TranscriptionResult:
        """Reads every target block, cropped from the page it is on.

        Args:
            all_pages: Every page image, indexed by TranscriptionTarget.page_index.
            targets: The blocks to read, as the Classifier settled them.
        """
        transcriptions = run_parallel(
            lambda target: self._transcribe_target(
                all_pages[target.page_index], target
            ),
            targets,
            self.MAX_PARALLEL_BLOCKS,
            progress_label="transcribing",
            progress_unit="block",
        )

        return TranscriptionResult(transcriptions)

    def _transcribe_target(
        self,
        page: Image,
        target: TranscriptionTarget,
    ) -> TranscriptionBlock:
        """Reads one block, as the kind of text the Classifier said it is."""
        block_image = self._extract_block_image(page, target)

        if target.transcription_type is TranscriptionType.TABLE:
            text = self._ocr_table_block_image(block_image)
        else:
            text = self._ocr_text_block_image(block_image)

        return TranscriptionBlock(block_id=target.block_id, text=text)

    def _extract_block_image(
        self,
        page: Image,
        target: TranscriptionTarget,
    ) -> Image:
        """Returns a cropped copy of the page image, containing only the block.

        The crop is padded by BLOCK_CROP_PADDING and kept inside the page.
        """
        x, y, width, height = target.bounding_box

        return page.crop(
            (
                max(0, x - BLOCK_CROP_PADDING),
                max(0, y - BLOCK_CROP_PADDING),
                min(page.width, x + width + BLOCK_CROP_PADDING),
                min(page.height, y + height + BLOCK_CROP_PADDING),
            )
        )

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
