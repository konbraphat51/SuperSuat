"""Nesting a transcribed document tree by the level of each of its headings."""

import json
import logging
from dataclasses import dataclass
from typing import Any

from PIL.Image import Image
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from ....LlmHelper import build_image_message, page_to_base64
from ....OcrSchema import OcrResult, OcrResultBlock, OcrResultBlockText
from .Leveler import MAX_ATTEMPT_COUNT, MAX_PAGES_PER_REQUEST, TOP_HEADING_LEVEL
from .LevelerSchema import HeadingLevels
from .prompt import OCR_RESULT_LEVELER_SYSTEM_PROMPT
from .SectionNester import flatten_blocks, nest_by_levels

logger = logging.getLogger(__name__)

# The block_type of a block that opens a section.
HEADING_BLOCK_TYPE = "heading"


@dataclass
class _Heading:
    """One heading of the document, as the model is asked about it."""

    block_index: int
    page_index: int | None  # the first page it is printed on, if known
    text: str


# Headings grouped by the page they are printed on, in document order.
_PageHeadings = list[tuple[int | None, list[_Heading]]]

# The parts of a message's content, as a chat model takes them.
_Content = list[str | dict[Any, Any]]


class OcrResultLeveler:
    """Gives every heading of a transcribed document its level, and nests the
    document tree to match.

    The counterpart of Leveler for a document already read into an OcrResult,
    whatever pipeline produced it: every heading is ranked afresh, so a tree
    whose headings all sit one level deep comes out nested as the document is.
    The heading text is known by now, so the model reads each heading's
    numbering and wording as well as how it is printed.

    The document is taken MAX_PAGES_PER_REQUEST heading-pages at a time, and
    every request after the first carries one page per level already decided,
    as Leveler does, to hold the hierarchy together across the parts.
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
        headings = _collect_headings(blocks)
        levels: dict[int, int] = {}

        parts = _split_into_parts(_group_by_page(headings))

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
        part: _PageHeadings,
        settled: list[_Heading],
        levels: dict[int, int],
        part_number: int,
    ) -> None:
        """Levels the headings of one part into `levels`, against those settled."""
        part_headings = [heading for _, headings in part for heading in headings]

        messages = self._build_messages(all_page_images, part, settled, levels)

        for attempt in range(1, MAX_ATTEMPT_COUNT + 1):
            heading_levels = self._request_levels(messages, part_number, attempt)
            messages.append(AIMessage(content=heading_levels.model_dump_json()))

            problems = _apply_levels(heading_levels, part_headings, levels)
            unleveled = [h for h in part_headings if h.block_index not in levels]

            if not problems and not unleveled:
                return

            logger.warning(
                "OcrResult leveler | part %d attempt %d left %d heading(s) unleveled",
                part_number,
                attempt,
                len(unleveled),
            )
            messages.append(HumanMessage(content=_retry_message(problems, unleveled)))

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
        part: _PageHeadings,
        settled: list[_Heading],
        levels: dict[int, int],
    ) -> list[BaseMessage]:
        """The system prompt, the levels settled so far, and this part's pages."""
        content: _Content = []

        content += _example_content(all_page_images, settled, levels)

        # the pages of this part, in page order, each labeled with its headings
        for page_index, page_headings in part:
            if page_index is None:
                continue

            named = "heading block" if len(page_headings) == 1 else "heading blocks"
            content += build_image_message(
                f"Page {page_index + 1}, holding {named} {_list_ids(page_headings)}:",
                page_to_base64(all_page_images[page_index]),
            )

        part_headings = [heading for _, headings in part for heading in headings]
        content.append(
            _text_part(
                "The headings to give a level to, in the order they are read in:\n"
                + _headings_json(part_headings, None)
            )
        )

        return [
            SystemMessage(content=OCR_RESULT_LEVELER_SYSTEM_PROMPT),
            HumanMessage(content=content),
        ]


def _collect_headings(blocks: list[OcrResultBlock]) -> list[_Heading]:
    """Every heading of the document, in document order."""
    return [
        _Heading(
            block_index=block.block_index,
            page_index=min(block.existing_pages) if block.existing_pages else None,
            text=block.text,
        )
        for block in blocks
        if isinstance(block, OcrResultBlockText)
        and block.block_type == HEADING_BLOCK_TYPE
    ]


def _group_by_page(headings: list[_Heading]) -> _PageHeadings:
    """Each run of headings printed on the same page, in document order."""
    grouped: _PageHeadings = []

    for heading in headings:
        if grouped and grouped[-1][0] == heading.page_index:
            grouped[-1][1].append(heading)
        else:
            grouped.append((heading.page_index, [heading]))

    return grouped


def _split_into_parts(page_headings: _PageHeadings) -> list[_PageHeadings]:
    """The heading pages in runs of at most MAX_PAGES_PER_REQUEST, in order."""
    return [
        page_headings[start : start + MAX_PAGES_PER_REQUEST]
        for start in range(0, len(page_headings), MAX_PAGES_PER_REQUEST)
    ]


def _example_content(
    all_page_images: list[Image],
    settled: list[_Heading],
    levels: dict[int, int],
) -> _Content:
    """One page per level settled so far, showing how that level is printed.

    The first heading of each level is the example: it is the one the levels
    after it were already judged against.
    """
    examples: dict[int, _Heading] = {}
    for heading in settled:
        examples.setdefault(levels[heading.block_index], heading)

    if not examples:
        return []

    content: _Content = [
        _text_part(
            "Levels already settled in the part of the document before this "
            "one. These pages are shown so that you can see how a heading of "
            "each level is printed; do not answer for their headings."
        )
    ]

    # one page often carries examples of two levels, and it is sent once
    examples_by_page: dict[int, list[tuple[int, _Heading]]] = {}
    for level, heading in sorted(examples.items()):
        if heading.page_index is not None:
            examples_by_page.setdefault(heading.page_index, []).append((level, heading))

    for page_index, shown in sorted(examples_by_page.items()):
        described = ", ".join(
            f"block {heading.block_index} as a level {level} heading"
            for level, heading in shown
        )
        content += build_image_message(
            f"Page {page_index + 1}, showing {described}:",
            page_to_base64(all_page_images[page_index]),
        )

    content.append(
        _text_part(
            "The levels settled so far, in the order the headings are read in:\n"
            + _headings_json(settled, levels)
        )
    )

    return content


def _headings_json(headings: list[_Heading], levels: dict[int, int] | None) -> str:
    """The headings as JSON, with their levels when `levels` is given."""
    listed: list[dict[str, object]] = []

    for heading in headings:
        entry: dict[str, object] = {"block_id": heading.block_index}
        if heading.page_index is not None:
            entry["page_number"] = heading.page_index + 1
        entry["text"] = heading.text
        if levels is not None:
            entry["heading_level"] = levels[heading.block_index]
        listed.append(entry)

    return json.dumps(listed, ensure_ascii=False, separators=(",", ":"))


def _apply_levels(
    heading_levels: HeadingLevels,
    headings: list[_Heading],
    levels: dict[int, int],
) -> list[str]:
    """Records each answered level into `levels`, and reports what could not
    be recorded."""
    asked_ids = {heading.block_index for heading in headings}
    problems: list[str] = []

    for level in heading_levels.levels:
        if level.target_block_id not in asked_ids:
            problems.append(
                f"Block {level.target_block_id} is not one of the headings you "
                "were asked about, so it was ignored."
            )
            continue

        if level.heading_level < TOP_HEADING_LEVEL:
            problems.append(
                f"Block {level.target_block_id} was given level "
                f"{level.heading_level}; the document's own title is level "
                f"{TOP_HEADING_LEVEL} and nothing sits above it."
            )
            continue

        levels[level.target_block_id] = level.heading_level

    return problems


def _retry_message(problems: list[str], unleveled: list[_Heading]) -> str:
    """What the model is told when its answer did not cover every heading."""
    lines = [f"- {problem}" for problem in problems]

    if unleveled:
        lines.append(
            f"- These headings still have no level: {_list_ids(unleveled)}. "
            "Give each one the level it holds in the hierarchy you just described."
        )

    return (
        "Every level you gave that could be used has been recorded, and the "
        "hierarchy you described stands. Answer again for what is still "
        "missing, keeping the levels you already gave:\n" + "\n".join(lines)
    )


def _text_part(text: str) -> dict[str, str]:
    """A text part of a message's content."""
    return {"type": "text", "text": text}


def _list_ids(headings: list[_Heading]) -> str:
    """The headings' block ids as one comma-separated list."""
    return ", ".join(str(heading.block_index) for heading in headings)
