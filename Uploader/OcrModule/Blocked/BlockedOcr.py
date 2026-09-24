"""The blocked OCR pipeline: find the blocks, settle what they are, then read them."""

import logging

from PIL.Image import Image

from ..Ocr import Ocr
from ..OcrSchema import OcrResult
from .Blocker.Blocker import Blocker
from .StructureOrganizer.Organizer import Organizer
from .StructureOrganizer.ProcessingSchema import build_transcription_targets
from .Transcriber.Transcriber import Transcriber

logger = logging.getLogger(__name__)


class BlockedOcr(Ocr):
    """Reads a document in three stages, each one over the whole document.

    A `Blocker` finds where the blocks of every page are, an `Organizer`
    settles what each of them is and how they nest into the document tree, and
    a `Transcriber` reads the text of each block last of all (see
    Docs/Plan.md).

    Reading last is the point of the order: by then every block has been
    called a paragraph, a table, a formula or a figure, so each one is read as
    the kind of thing it is - and a figure, whose content is the picture, is
    not read at all.

    Which model each stage runs on is the caller's choice: a stage is handed in
    already built, so a local layout model and a remote chat model - or a
    faster, cheaper mix - are the same pipeline."""

    def __init__(
        self,
        blocker: Blocker,
        organizer: Organizer,
        transcriber: Transcriber,
    ) -> None:
        """
        Args:
            blocker: Finds where the blocks of each page are.
            organizer: Settles what the blocks are and how they nest.
            transcriber: Reads the text of the blocks that hold text.
        """
        self.blocker = blocker
        self.organizer = organizer
        self.transcriber = transcriber

    def ocr(
        self,
        all_page_images: list[Image],
    ) -> OcrResult:
        """Reads every page, in order, into a single document tree."""
        logger.info("blocked OCR | %d page(s)", len(all_page_images))

        blocker_result = self.blocker.block(all_page_images)

        processing_blocks = self.organizer.organize(
            all_page_images=all_page_images,
            blocker_result=blocker_result,
        )

        transcription_result = self.transcriber.transcribe(
            all_pages=all_page_images,
            targets=build_transcription_targets(processing_blocks),
        )

        return self.organizer.export(
            processing_blocks=processing_blocks,
            transcription_result=transcription_result,
        )
