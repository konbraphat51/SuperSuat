"""Nesting a transcribed document tree by the level of each of its headings."""

import logging

from PIL.Image import Image
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from OcrModule.LlmHelper import build_image_message, page_to_base64
from OcrModule.OcrSchema import OcrResult

from .Headings import (
    Content,
    Heading,
    PageHeadings,
    apply_levels,
    collect_headings,
    format_level,
    group_by_page,
    headings_json,
    list_ids,
    retry_message,
    split_into_parts,
    text_part,
)
from .LevelerSchema import HeadingLevels
from .prompt import LEVELER_SYSTEM_PROMPT
from .SectionNester import flatten_blocks, nest_by_levels

logger = logging.getLogger(__name__)

# Heading pages sent in one request; the rest of the document follows in later parts.
MAX_PAGES_PER_REQUEST = 8

# Guard against a model that keeps leaving headings unanswered.
MAX_ATTEMPT_COUNT = 3


class OcrResultLeveler:
    """Gives every heading of a transcribed document its level, and nests the
    document tree to match.

    Works on a document already read into an OcrResult, whatever pipeline
    produced it: every heading is ranked afresh, so a tree whose headings all
    sit one level deep comes out nested as the document is.
    The heading text is known by now, so the model reads each heading's
    numbering and wording as well as how it is printed.

    The document is taken MAX_PAGES_PER_REQUEST heading-pages at a time, and
    every request after the first carries one page per level already decided,
    to hold the hierarchy together across the parts.
    """

    def __init__(
        self,
        leveler_model: BaseChatModel,
    ) -> None:
        """
        Args:
            leveler_model: Multimodal chat model that assigns the levels.
        """
        self.leveler_model = leveler_model.with_structured_output(HeadingLevels)

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
                Only the pages holding a heading are shown to the model.
            ocr_result: The transcribed document, nested in any way.

        Raises:
            RuntimeError: A heading was still left without a level after
                MAX_ATTEMPT_COUNT attempts.
        """
        blocks = flatten_blocks(ocr_result.root_section)
        headings = collect_headings(blocks)
        levels: dict[int, float] = {}

        parts = split_into_parts(group_by_page(headings), MAX_PAGES_PER_REQUEST)

        for part_number, part in enumerate(parts, start=1):
            logger.info(
                "OcrResult leveler | part %d/%d: %d page(s)",
                part_number,
                len(parts),
                len(part),
            )
            self._level_part(
                all_page_images=all_page_images,
                part=part,
                settled=[h for h in headings if h.block_index in levels],
                levels=levels,
                part_number=part_number,
            )

        logger.info("OcrResult leveler | %d heading(s) leveled", len(headings))

        root_section = nest_by_levels(
            ocr_result.root_section.block_index, blocks, levels
        )

        return OcrResult(root_section=root_section)

    def _level_part(
        self,
        all_page_images: list[Image],
        part: PageHeadings,
        settled: list[Heading],
        levels: dict[int, float],
        part_number: int,
    ) -> None:
        """Levels the headings of one part into `levels`, against those settled."""
        part_headings = [heading for _, headings in part for heading in headings]

        messages = self._build_messages(all_page_images, part, settled, levels)

        for attempt in range(1, MAX_ATTEMPT_COUNT + 1):
            heading_levels = self._request_levels(messages, part_number, attempt)
            messages.append(AIMessage(content=heading_levels.model_dump_json()))

            problems = apply_levels(heading_levels, part_headings, levels)
            unleveled = [h for h in part_headings if h.block_index not in levels]

            if not problems and not unleveled:
                return

            logger.warning(
                "OcrResult leveler | part %d attempt %d left %d heading(s) unleveled",
                part_number,
                attempt,
                len(unleveled),
            )
            messages.append(HumanMessage(content=retry_message(problems, unleveled)))

        unleveled_count = len([h for h in part_headings if h.block_index not in levels])
        raise RuntimeError(
            f"{unleveled_count} heading(s) were left without a level after "
            f"{MAX_ATTEMPT_COUNT} attempts."
        )

    def _request_levels(
        self,
        messages: list[BaseMessage],
        part_number: int,
        attempt: int,
    ) -> HeadingLevels:
        """Asks the model for the level of every heading of this part."""
        heading_levels = self.leveler_model.invoke(messages)

        if not isinstance(heading_levels, HeadingLevels):
            raise RuntimeError("The leveler model returned no heading levels.")

        logger.info(
            "OcrResult leveler | part %d attempt %d: %d level(s)",
            part_number,
            attempt,
            len(heading_levels.levels),
        )

        return heading_levels

    def _build_messages(
        self,
        all_page_images: list[Image],
        part: PageHeadings,
        settled: list[Heading],
        levels: dict[int, float],
    ) -> list[BaseMessage]:
        """The system prompt, the levels settled so far, and this part's pages."""
        content: Content = []

        content += _example_content(all_page_images, settled, levels)

        # the pages of this part, in page order, each labeled with its headings
        for page_index, page_headings in part:
            if page_index is None:
                continue

            named = "heading block" if len(page_headings) == 1 else "heading blocks"
            content += build_image_message(
                f"Page {page_index + 1}, holding {named} {list_ids(page_headings)}:",
                page_to_base64(all_page_images[page_index]),
            )

        part_headings = [heading for _, headings in part for heading in headings]
        content.append(
            text_part(
                "The headings to give a level to, in the order they are read in:\n"
                + headings_json(part_headings, None)
            )
        )

        return [
            SystemMessage(content=LEVELER_SYSTEM_PROMPT),
            HumanMessage(content=content),
        ]


def _example_content(
    all_page_images: list[Image],
    settled: list[Heading],
    levels: dict[int, float],
) -> Content:
    """One page per level settled so far, showing how that level is printed.

    The first heading of each level is the example: it is the one the levels
    after it were already judged against.
    """
    examples: dict[float, Heading] = {}
    for heading in settled:
        examples.setdefault(levels[heading.block_index], heading)

    if not examples:
        return []

    content: Content = [
        text_part(
            "Levels already settled in the part of the document before this "
            "one. These pages are shown so that you can see how a heading of "
            "each level is printed; do not answer for their headings."
        )
    ]

    # one page often carries examples of two levels, and it is sent once
    examples_by_page: dict[int, list[tuple[float, Heading]]] = {}
    for level, heading in sorted(examples.items()):
        if heading.page_index is not None:
            examples_by_page.setdefault(heading.page_index, []).append((level, heading))

    for page_index, shown in sorted(examples_by_page.items()):
        described = ", ".join(
            f"block {heading.block_index} as a level {format_level(level)} heading"
            for level, heading in shown
        )
        content += build_image_message(
            f"Page {page_index + 1}, showing {described}:",
            page_to_base64(all_page_images[page_index]),
        )

    content.append(
        text_part(
            "The levels settled so far, in the order the headings are read in:\n"
            + headings_json(settled, levels)
        )
    )

    return content
