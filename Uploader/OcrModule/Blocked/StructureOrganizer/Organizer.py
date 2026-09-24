"""Settling the detected blocks into a document structure, and writing it out."""

import logging
from copy import deepcopy

from PIL.Image import Image
from langchain_core.language_models import BaseChatModel

from ...OcrSchema import OcrResult
from ..Blocker.BlockRenderer import BlockRenderer
from ..PageParallel import DEFAULT_MAX_PARALLEL_PAGES, run_parallel
from ..Schema import BlockerResult, TranscriptionResult
from .Classifier.Classifier import Classifier
from .DataExporter import export_processing_blocks_to_ocr_result
from .Leveler.Leveler import Leveler
from .ProcessingSchema import (
    ProcessingBlock,
    apply_transcriptions,
    convert_blocker_result_to_processing_blocks,
)

logger = logging.getLogger(__name__)


class Organizer:
    """Turns the blocks a Blocker found into the document's structure.

    Two model stages, split by what a decision needs to see: the Classifier
    settles one page at a time, and the Leveler ranks every heading of the
    document against the others once the pages are in.

    Attributes:
        MAX_PARALLEL_PAGES: How many pages are classified at once.
    """

    MAX_PARALLEL_PAGES = DEFAULT_MAX_PARALLEL_PAGES

    def __init__(
        self,
        classifier_model: BaseChatModel,
        leveler_model: BaseChatModel | None = None,
    ) -> None:
        """
        Args:
            classifier_model: Multimodal chat model that settles each page.
            leveler_model: Multimodal chat model that ranks the headings.
                Defaults to the classifier's, which is the only model most
                callers have; ranking headings is the lighter job of the two,
                so a cheaper model can be passed here.
        """
        self.classifier = Classifier(classifier_model=classifier_model)
        self.leveler = Leveler(leveler_model=leveler_model or classifier_model)
        self.block_renderer = BlockRenderer()

    def organize(
        self,
        all_page_images: list[Image],
        blocker_result: BlockerResult,
    ) -> list[ProcessingBlock]:
        """Settles what every block is, in reading order, headings ranked.

        Nothing has been read yet: this is what decides how each block is to
        be read, so it runs before the Transcriber.

        Args:
            all_page_images: Every page of the document, as scanned, 0-indexed.
            blocker_result: The blocks detected by a Blocker.

        Returns:
            Every block of the document, in reading order, labeled - text
            blocks still empty, for the Transcriber to fill in.
        """
        processing_blocks = convert_blocker_result_to_processing_blocks(blocker_result)

        page_blocks = _group_blocks_by_page(processing_blocks, len(all_page_images))
        # what the pages read of each other, frozen before any of them is
        # settled, so no page ever sees another one half-classified
        context_page_blocks = deepcopy(page_blocks)

        # settle each page, several pages at once
        settled_pages = run_parallel(
            lambda page_index: self._scan_page(
                page_index=page_index,
                all_page_images=all_page_images,
                page_blocks=page_blocks[page_index],
                context_page_blocks=context_page_blocks,
            ),
            range(len(all_page_images)),
            self.MAX_PARALLEL_PAGES,
            progress_label="classifying",
        )

        processing_blocks = [block for page in settled_pages for block in page]

        # rank the headings of every page against each other
        self.leveler.level_headings(
            all_page_images=all_page_images,
            processing_blocks=processing_blocks,
        )

        return processing_blocks

    def export(
        self,
        processing_blocks: list[ProcessingBlock],
        transcription_result: TranscriptionResult,
    ) -> OcrResult:
        """Writes the transcriptions onto the blocks and builds the document tree.

        Args:
            processing_blocks: Every block of the document, in reading order,
                as `organize` settled them.
            transcription_result: What the Transcriber read of those blocks.
        """
        apply_transcriptions(processing_blocks, transcription_result)

        return export_processing_blocks_to_ocr_result(processing_blocks)

    def _scan_page(
        self,
        page_index: int,
        all_page_images: list[Image],
        page_blocks: list[ProcessingBlock],
        context_page_blocks: list[list[ProcessingBlock]],
    ) -> list[ProcessingBlock]:
        """Settles one page, drawing its blocks onto it for the model first.

        The annotated page is drawn here, inside the page's own work, so only
        the pages being worked on hold one - a document's worth of annotated
        copies is the same memory again as the document itself.
        """
        page_image_rendered = self.block_renderer.render_page(
            all_page_images[page_index],
            context_page_blocks[page_index],
        )

        return self.classifier.scan_page(
            page_index=page_index,
            all_page_images=all_page_images,
            page_image_rendered=page_image_rendered,
            page_blocks=page_blocks,
            context_page_blocks=context_page_blocks,
        )


def _group_blocks_by_page(
    processing_blocks: list[ProcessingBlock],
    page_count: int,
) -> list[list[ProcessingBlock]]:
    """The blocks split into one list per page, in reading order.

    A page the Blocker found nothing on gets an empty list, so every page has
    a list of its own to be settled in.
    """
    grouped: list[list[ProcessingBlock]] = [[] for _ in range(page_count)]

    for block in processing_blocks:
        grouped[block.page_index].append(block)

    return grouped
