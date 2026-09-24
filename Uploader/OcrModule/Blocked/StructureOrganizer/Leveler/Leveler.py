"""Placing every heading of the document in one hierarchy of levels."""

import json
import logging

from PIL.Image import Image
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.messages.content import create_text_block

from ....LlmHelper import build_image_message, page_to_base64
from ..ProcessingSchema import ProcessingBlock, ProcessingBlockTextHeading
from .LevelerSchema import HeadingLevels
from .prompt import LEVELER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# The level of the document's own title, which nothing sits above.
TOP_HEADING_LEVEL = 1

# How many heading-bearing pages are asked about in one request. Every one of
# them is a page image, so a document with headings on a hundred pages would
# otherwise be one request of a hundred images - past what an API accepts,
# never mind what a model can hold in view at once.
MAX_PAGES_PER_REQUEST = 8

# Guard against a model that keeps leaving headings unanswered.
MAX_ATTEMPT_COUNT = 3

# Page groups, each with the headings found on the page.
PageHeadings = list[tuple[int, list[ProcessingBlockTextHeading]]]


class Leveler:
    """Gives every heading of the document the level it holds in the hierarchy.

    This is the one decision a page cannot make on its own: a level means
    nothing except against the rest of the document, so the Classifier only
    says which blocks are headings and this stage ranks them.

    The document is taken MAX_PAGES_PER_REQUEST heading-pages at a time, and
    every request after the first carries one page per level already decided,
    as an example of how a heading of that level is printed. That is what
    holds the hierarchy together across the parts: the model is not asked to
    remember what a level 2 looked like, it is shown one.
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

    def level_headings(
        self,
        all_page_images: list[Image],
        processing_blocks: list[ProcessingBlock],
    ) -> None:
        """Sets heading_level on every heading, editing the blocks in place.

        Args:
            all_page_images: Every page of the document, as scanned, 0-indexed.
                Only the pages holding a heading are shown to the model.
            processing_blocks: Every block of the document, in current order,
                as the Classifier left them.

        Raises:
            RuntimeError: A heading was still left without a level after
                MAX_ATTEMPT_COUNT attempts. The run stops there rather than
                writing down a document whose hierarchy is half guessed.
        """
        headings = _collect_headings(processing_blocks)

        if not headings:
            logger.info("leveler | the document holds no heading")
            return

        page_headings = _group_by_page(headings)
        parts = _split_into_parts(page_headings)

        for part_number, part in enumerate(parts, start=1):
            logger.info(
                "leveler | part %d/%d: %d page(s)",
                part_number,
                len(parts),
                len(part),
            )
            self._level_part(
                all_page_images=all_page_images,
                part=part,
                leveled_headings=_leveled(headings),
                part_number=part_number,
            )

        logger.info("leveler | %d heading(s) leveled", len(headings))

    def _level_part(
        self,
        all_page_images: list[Image],
        part: PageHeadings,
        leveled_headings: list[ProcessingBlockTextHeading],
        part_number: int,
    ) -> None:
        """Levels the headings of one part, against the levels already given."""
        part_headings = [heading for _, headings in part for heading in headings]

        messages = self._build_messages(
            all_page_images=all_page_images,
            part=part,
            leveled_headings=leveled_headings,
        )

        for attempt in range(1, MAX_ATTEMPT_COUNT + 1):
            heading_levels = self._request_levels(messages, part_number, attempt)
            messages.append(AIMessage(content=heading_levels.model_dump_json()))

            problems = _apply_levels(heading_levels, part_headings)
            unleveled = [
                heading for heading in part_headings if heading.heading_level is None
            ]

            if not problems and not unleveled:
                return

            logger.warning(
                "leveler | part %d attempt %d left %d heading(s) unleveled",
                part_number,
                attempt,
                len(unleveled),
            )
            messages.append(HumanMessage(content=_retry_message(problems, unleveled)))

        raise RuntimeError(
            f"{len([h for h in part_headings if h.heading_level is None])} heading(s) "
            f"were left without a level after {MAX_ATTEMPT_COUNT} attempts."
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
            "leveler | part %d attempt %d: %d level(s)",
            part_number,
            attempt,
            len(heading_levels.levels),
        )

        return heading_levels

    def _build_messages(
        self,
        all_page_images: list[Image],
        part: PageHeadings,
        leveled_headings: list[ProcessingBlockTextHeading],
    ) -> list[BaseMessage]:
        """The system prompt, the levels settled so far, and this part's pages."""
        content: list[dict] = []

        content += self._example_content(all_page_images, leveled_headings)

        # the pages of this part, in page order, each labeled with its headings
        for page_index, page_headings in part:
            named = "heading block" if len(page_headings) == 1 else "heading blocks"
            content += build_image_message(
                f"Page {page_index + 1}, holding {named} {_list_ids(page_headings)}:",
                page_to_base64(all_page_images[page_index]),
            )

        content.append(
            create_text_block(_headings_text([h for _, hs in part for h in hs]))
        )

        return [
            SystemMessage(content=LEVELER_SYSTEM_PROMPT),
            HumanMessage(content=content),
        ]

    def _example_content(
        self,
        all_page_images: list[Image],
        leveled_headings: list[ProcessingBlockTextHeading],
    ) -> list[dict]:
        """One page per level settled so far, showing how that level is printed.

        Without these, each part would rank its own headings from scratch and
        the parts would not agree: the same size of heading would be a level 2
        in one part and a level 3 in the next.
        """
        examples = _level_examples(leveled_headings)

        if not examples:
            return []

        content: list[dict] = [
            create_text_block(
                "Levels already settled in the part of the document before this "
                "one. These pages are shown so that you can see how a heading of "
                "each level is printed; do not answer for their headings."
            )
        ]

        for page_index, shown_levels in _examples_by_page(examples):
            content += build_image_message(
                f"Page {page_index + 1}, showing {_describe_levels(shown_levels)}:",
                page_to_base64(all_page_images[page_index]),
            )

        content.append(create_text_block(_settled_levels_text(leveled_headings)))

        return content


def _collect_headings(
    processing_blocks: list[ProcessingBlock],
) -> list[ProcessingBlockTextHeading]:
    """Every heading of the document, in document order."""
    return [
        block
        for block in processing_blocks
        if isinstance(block, ProcessingBlockTextHeading)
    ]


def _leveled(
    headings: list[ProcessingBlockTextHeading],
) -> list[ProcessingBlockTextHeading]:
    """The headings that already carry a level, in document order."""
    return [heading for heading in headings if heading.heading_level is not None]


def _group_by_page(
    headings: list[ProcessingBlockTextHeading],
) -> PageHeadings:
    """The headings grouped by the page they are on, in page order."""
    grouped: dict[int, list[ProcessingBlockTextHeading]] = {}

    for heading in headings:
        grouped.setdefault(heading.page_index, []).append(heading)

    return sorted(grouped.items())


def _split_into_parts(page_headings: PageHeadings) -> list[PageHeadings]:
    """The heading pages in runs of at most MAX_PAGES_PER_REQUEST, in order."""
    return [
        page_headings[start : start + MAX_PAGES_PER_REQUEST]
        for start in range(0, len(page_headings), MAX_PAGES_PER_REQUEST)
    ]


def _level_examples(
    leveled_headings: list[ProcessingBlockTextHeading],
) -> dict[int, ProcessingBlockTextHeading]:
    """One heading per level settled so far - the first one of each level.

    The first is as good as any and is the one the levels after it were
    already judged against.
    """
    examples: dict[int, ProcessingBlockTextHeading] = {}

    for heading in leveled_headings:
        assert heading.heading_level is not None
        examples.setdefault(heading.heading_level, heading)

    return examples


def _examples_by_page(
    examples: dict[int, ProcessingBlockTextHeading],
) -> list[tuple[int, list[tuple[int, ProcessingBlockTextHeading]]]]:
    """The example headings grouped by page, in page order.

    One page often carries examples of two levels, and it is sent once.
    """
    grouped: dict[int, list[tuple[int, ProcessingBlockTextHeading]]] = {}

    for level, heading in sorted(examples.items()):
        grouped.setdefault(heading.page_index, []).append((level, heading))

    return sorted(grouped.items())


def _describe_levels(
    shown_levels: list[tuple[int, ProcessingBlockTextHeading]],
) -> str:
    """What a page's example headings are, as one phrase."""
    return ", ".join(
        f"block {heading.block_id} as a level {level} heading"
        for level, heading in shown_levels
    )


def _settled_levels_text(leveled_headings: list[ProcessingBlockTextHeading]) -> str:
    """The levels settled so far, as JSON, in document order."""
    listed = [
        {
            "block_id": heading.block_id,
            "page_number": heading.page_index + 1,
            "heading_level": heading.heading_level,
        }
        for heading in leveled_headings
    ]

    return (
        "The levels settled so far, in the order the headings are read in:\n"
        f"{json.dumps(listed, ensure_ascii=False, separators=(',', ':'))}"
    )


def _headings_text(headings: list[ProcessingBlockTextHeading]) -> str:
    """The headings to answer for, as JSON, in document order.

    A heading has no text yet - it is read after the structure is settled - so
    what identifies it here is its id and the page it is printed on.
    """
    listed = [
        {
            "block_id": heading.block_id,
            "page_number": heading.page_index + 1,
        }
        for heading in headings
    ]

    return (
        "The headings to give a level to, in the order they are read in:\n"
        f"{json.dumps(listed, ensure_ascii=False, separators=(',', ':'))}"
    )


def _apply_levels(
    heading_levels: HeadingLevels,
    headings: list[ProcessingBlockTextHeading],
) -> list[str]:
    """Writes each answered level onto its heading, and reports what could not
    be written."""
    headings_by_id = {heading.block_id: heading for heading in headings}
    problems: list[str] = []

    for level in heading_levels.levels:
        heading = headings_by_id.get(level.target_block_id)

        if heading is None:
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

        heading.heading_level = level.heading_level

    return problems


def _retry_message(
    problems: list[str],
    unleveled: list[ProcessingBlockTextHeading],
) -> str:
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


def _list_ids(headings: list[ProcessingBlockTextHeading]) -> str:
    """The headings' block ids as one comma-separated list."""
    return ", ".join(str(heading.block_id) for heading in headings)
