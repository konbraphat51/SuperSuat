from copy import deepcopy
from PIL.Image import Image
from langchain_core.language_models import BaseChatModel
from ...OcrSchema import OcrResult
from ..Schema import (
    BlockerResult,
    Block,
    TranscriptionResult,
)
from ..PageParallel import DEFAULT_MAX_PARALLEL_PAGES, map_pages
from .ProcessingSchema import (
    ProcessingBlock,
    ProcessingBlockText,
    ProcessingBlockTextHeading,
    ProcessingBlockFigure,
    convert_blocker_result_to_processing_blocks,
)

from .Classifier.Classifier import Classifier
from .Leveler.Leveler import Leveler
from .DataExporter import export_processing_blocks_to_ocr_result


class Organizer:
    """Settles the detected blocks into a document structure.

    Attributes:
        MAX_PARALLEL_PAGES: How many pages are classified at once.
    """

    MAX_PARALLEL_PAGES = DEFAULT_MAX_PARALLEL_PAGES

    def __init__(
        self,
        organizer_model: BaseChatModel,
    ) -> None:
        self.classifier = Classifier(classifier_model=organizer_model)
        self.leveler = Leveler(leveler_model=organizer_model)

    def organize(
        self,
        all_page_images: list[Image],
        all_page_images_rendered: list[Image],
        blocker_result: BlockerResult,
        transcription_result: TranscriptionResult,
    ) -> OcrResult:
        # convert data
        processing_blocks = convert_blocker_result_to_processing_blocks(
            blocker_result=blocker_result,
            transcription_result=transcription_result,
        )

        page_blocks = _group_blocks_by_page(processing_blocks, len(all_page_images))
        # what the pages read of each other, frozen before any of them is
        # settled, so no page ever sees another one half-classified
        context_page_blocks = deepcopy(page_blocks)

        # settle each page, several pages at once
        settled_pages = map_pages(
            lambda page_index: self._scan_page(
                page_index=page_index,
                all_page_images=all_page_images,
                page_image_rendered=all_page_images_rendered[page_index],
                page_blocks=page_blocks[page_index],
                context_page_blocks=context_page_blocks,
            ),
            range(len(all_page_images)),
            self.MAX_PARALLEL_PAGES,
        )

        processing_blocks = [block for page in settled_pages for block in page]

        # rank the headings of every page against each other
        self.leveler.level_headings(
            all_page_images=all_page_images,
            processing_blocks=processing_blocks,
        )

        # build the document tree out of the settled blocks
        return export_processing_blocks_to_ocr_result(processing_blocks)

    def _scan_page(
        self,
        page_index: int,
        all_page_images: list[Image],
        page_image_rendered: Image,
        page_blocks: list[ProcessingBlock],
        context_page_blocks: list[list[ProcessingBlock]],
    ) -> list[ProcessingBlock]:
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
