"""The blocked OCR pipeline: blocks a page, reads each block, then settles the structure."""

import logging

from PIL.Image import Image

from ..Ocr import Ocr
from ..OcrSchema import OcrResult
from .Blocker.Blocker import Blocker
from .Blocker.BlockRenderer import BlockRenderer
from .StructureOrganizer.Organizer import Organizer
from .Transcriber.Transcriber import Transcriber

logger = logging.getLogger(__name__)


class BlockedOcr(Ocr):
    """Reads a document in three stages, each one over the whole document.

    A `Blocker` finds the blocks of every page, a `Transcriber` reads the text
    of each of them, and an `Organizer` settles what the blocks are and how
    they nest into the document tree (see Docs/Plan.md).

    Which model each stage runs on is the caller's choice: a stage is handed in
    already built, so a local layout model and a remote chat model - or a
    faster, cheaper mix - are the same pipeline."""

    def __init__(
        self,
        blocker: Blocker,
        transcriber: Transcriber,
        organizer: Organizer,
    ) -> None:
        """
        Args:
            blocker: Finds the blocks of each page.
            transcriber: Reads the text of the blocks the blocker found.
            organizer: Settles the blocks into the document structure.
        """
        self.blocker = blocker
        self.transcriber = transcriber
        self.organizer = organizer
        self.block_renderer = BlockRenderer()

    def ocr(
        self,
        all_page_images: list[Image],
    ) -> OcrResult:
        """Reads every page, in order, into a single document tree."""
        logger.info("blocked OCR | %d page(s)", len(all_page_images))

        blocker_result = self.blocker.block(all_page_images)

        transcription_result = self.transcriber.transcribe(
            all_pages=all_page_images,
            blocker_result=blocker_result,
        )

        # the organizer's model is shown the blocks outlined on the page, so it
        # can tell which block on the page a block_id names
        all_page_images_rendered = self.block_renderer.render(
            pages=all_page_images,
            blocker_result=blocker_result,
        )

        return self.organizer.organize(
            all_page_images=all_page_images,
            all_page_images_rendered=all_page_images_rendered,
            blocker_result=blocker_result,
            transcription_result=transcription_result,
        )
