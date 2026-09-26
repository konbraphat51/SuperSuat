"""Nesting a transcribed document tree by the level of each of its headings."""

import logging

from PIL.Image import Image
from langchain_core.language_models import BaseChatModel

from OcrModule.OcrSchema import OcrResult

from .Headings import collect_headings
from .PageLeveler import PageLeveler
from .SectionNester import flatten_blocks, nest_by_levels
from .SkeletonLeveler import SkeletonLeveler
from .TableOfContentsText import collect_tables_of_contents

logger = logging.getLogger(__name__)


class OcrResultLeveler:
    """Gives every heading of a transcribed document its level, and nests the
    document tree to match.

    Works on a document already read into an OcrResult, whatever pipeline
    produced it: every heading is ranked afresh, so a tree whose headings all
    sit one level deep comes out nested as the document is.

    The hierarchy is first laid out from the headings' text and the document's
    tables of contents, without page images. Only the headings the text leaves
    open are then decided from their printed pages, fitted between the settled
    levels with a decimal level where they rank between two.
    """

    def __init__(
        self,
        leveler_model: BaseChatModel,
    ) -> None:
        """
        Args:
            leveler_model: Multimodal chat model that assigns the levels.
        """
        self.skeleton_leveler = SkeletonLeveler(leveler_model)
        self.page_leveler = PageLeveler(leveler_model)

    def level_ocr_result(
        self,
        all_page_images: list[Image],
        ocr_result: OcrResult,
    ) -> OcrResult:
        """The document tree nested by the level of every heading.

        The given tree is left as it is; the new one holds the same blocks, not
        copies, under new sections.

        Args:
            all_page_images: Every page of the document, as scanned, 0-indexed.
                Only the pages of the headings the text leaves open are shown
                to the model.
            ocr_result: The transcribed document, nested in any way.

        Raises:
            RuntimeError: A heading was still left without a level after
                MAX_ATTEMPT_COUNT attempts.
        """
        blocks = flatten_blocks(ocr_result.root_section)
        headings = collect_headings(blocks)
        levels: dict[int, float] = {}

        if headings:
            skeleton = self.skeleton_leveler.level(
                headings, collect_tables_of_contents(blocks)
            )
            levels = self.page_leveler.level(all_page_images, headings, skeleton)

        logger.info("OcrResult leveler | %d heading(s) leveled", len(headings))

        root_section = nest_by_levels(
            ocr_result.root_section.block_index, blocks, levels
        )

        return OcrResult(root_section=root_section)
