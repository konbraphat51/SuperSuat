"""Deciding, from the printed pages, the levels of the headings their text left open."""

import json
import logging
from collections.abc import Sequence

from PIL.Image import Image
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from OcrModule.LlmHelper import build_image_message, page_to_base64

from .Headings import (
    Content,
    Heading,
    PageHeadings,
    format_level,
    group_by_page,
    headings_json,
    list_ids,
    split_into_parts,
    text_part,
)
from .LevelerSchema import HeadingLevels
from .LevelRequest import request_levels
from .prompt import PAGE_SYSTEM_PROMPT
from .SkeletonLeveler import Skeleton

logger = logging.getLogger(__name__)

# Pages holding a heading to decide, sent in one request; the rest follow in later parts.
MAX_PAGES_PER_REQUEST = 16


class PageLeveler:
    """Decides the level of every heading the skeleton left open, from the
    pages it is printed on, against the levels the skeleton settled.

    Only the pages of those headings are sent, MAX_PAGES_PER_REQUEST at a time,
    with one example page per settled level and the whole outline as text.
    """

    def __init__(
        self,
        leveler_model: BaseChatModel,
    ) -> None:
        """
        Args:
            leveler_model: Multimodal chat model that decides the levels.
        """
        self.page_model = leveler_model.with_structured_output(HeadingLevels)

    def level(
        self,
        all_page_images: Sequence[Image],
        headings: list[Heading],
        skeleton: Skeleton,
    ) -> dict[int, float]:
        """The final level of every heading, keyed by block_index.

        Args:
            all_page_images: Every page of the document, as scanned, 0-indexed;
                only the pages sent are read from it, so it may render lazily.
            headings: Every heading of the document, in document order.
            skeleton: The levels judged from text, and the headings left open.

        Raises:
            RuntimeError: A heading was still left without a level after
                MAX_ATTEMPT_COUNT attempts.
        """
        settled = {
            block_id: level
            for block_id, level in skeleton.levels.items()
            if block_id not in skeleton.uncertain
        }
        open_headings = [h for h in headings if h.block_index in skeleton.uncertain]
        parts = split_into_parts(group_by_page(open_headings), MAX_PAGES_PER_REQUEST)

        for part_number, part in enumerate(parts, start=1):
            logger.info(
                "Page leveler | part %d/%d: %d page(s)",
                part_number,
                len(parts),
                len(part),
            )
            request_levels(
                model=self.page_model,
                answer_type=HeadingLevels,
                messages=_build_messages(
                    all_page_images, headings, part, skeleton, settled
                ),
                headings=[heading for _, page in part for heading in page],
                levels=settled,
                label=f"page part {part_number}",
            )

        return settled


def _build_messages(
    all_page_images: Sequence[Image],
    headings: list[Heading],
    part: PageHeadings,
    skeleton: Skeleton,
    settled: dict[int, float],
) -> list[BaseMessage]:
    """The system prompt, the example pages, the outline, and this part's pages."""
    part_pages = {page_index for page_index, _ in part if page_index is not None}
    content: Content = _example_content(all_page_images, headings, settled, part_pages)

    content.append(
        text_part(
            "The outline of the whole document, in the order the headings are "
            "read in:\n" + _outline_json(headings, skeleton, settled)
        )
    )

    # the pages of this part, in page order, each labeled with its headings
    for page_index, page_headings in part:
        if page_index is None:
            continue

        named = "heading block" if len(page_headings) == 1 else "heading blocks"
        content += build_image_message(
            f"Page {page_index + 1}, holding {named} {list_ids(page_headings)} "
            "to decide:",
            page_to_base64(all_page_images[page_index]),
        )

    part_headings = [heading for _, page in part for heading in page]
    content.append(
        text_part(
            "The headings to decide in this request, in the order they are read "
            "in:\n" + headings_json(part_headings, None)
        )
    )

    return [
        SystemMessage(content=PAGE_SYSTEM_PROMPT),
        HumanMessage(content=content),
    ]


def _example_content(
    all_page_images: Sequence[Image],
    headings: list[Heading],
    settled: dict[int, float],
    part_pages: set[int],
) -> Content:
    """One page per settled level, showing how that level is printed.

    The first heading of each level is the example. A page this part sends
    anyway is not sent again as an example.
    """
    examples: dict[float, Heading] = {}
    for heading in headings:
        level = settled.get(heading.block_index)
        if level is not None and heading.page_index is not None:
            examples.setdefault(level, heading)

    # one page often carries examples of two levels, and it is sent once
    examples_by_page: dict[int, list[tuple[float, Heading]]] = {}
    for level, heading in sorted(examples.items()):
        assert heading.page_index is not None
        if heading.page_index not in part_pages:
            examples_by_page.setdefault(heading.page_index, []).append((level, heading))

    if not examples_by_page:
        return []

    content: Content = [
        text_part(
            "These pages are shown so that you can see how a heading of each "
            "settled level is printed; do not answer for their headings."
        )
    ]

    for page_index, shown in sorted(examples_by_page.items()):
        described = ", ".join(
            f"block {heading.block_index} as a level {format_level(level)} heading"
            for level, heading in shown
        )
        content += build_image_message(
            f"Page {page_index + 1}, showing {described}:",
            page_to_base64(all_page_images[page_index]),
        )

    return content


def _outline_json(
    headings: list[Heading],
    skeleton: Skeleton,
    settled: dict[int, float],
) -> str:
    """Every heading as JSON: settled ones with their level, open ones marked
    to decide with the level the text suggested."""
    listed: list[dict[str, object]] = []

    for heading in headings:
        entry: dict[str, object] = {"block_id": heading.block_index}
        if heading.page_index is not None:
            entry["page_number"] = heading.page_index + 1
        entry["text"] = heading.text

        level = settled.get(heading.block_index)
        if level is not None:
            entry["heading_level"] = format_level(level)
        else:
            entry["decide"] = True
            entry["draft_level"] = format_level(skeleton.levels[heading.block_index])

        listed.append(entry)

    return json.dumps(listed, ensure_ascii=False, separators=(",", ":"))
