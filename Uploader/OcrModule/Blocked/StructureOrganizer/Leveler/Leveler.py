"""Placing every heading of the document in one hierarchy of levels."""

import json
import logging
from PIL.Image import Image
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.messages.content import create_text_block
from ....LlmHelper import build_image_message, pil_to_base64
from ..ProcessingSchema import ProcessingBlock, ProcessingBlockTextHeading
from .LevelerSchema import HeadingLevels
from .prompt import LEVELER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# The level of the document's own title, which nothing sits above.
TOP_HEADING_LEVEL = 1

# Guard against a model that keeps leaving headings unanswered.
MAX_ATTEMPT_COUNT = 3


class Leveler:
    """Gives every heading of the document the level it holds in the hierarchy.

    This is the one decision a page cannot make on its own: a level means
    nothing except against the rest of the document, so the Classifier only
    says which blocks are headings and this stage ranks them all at once,
    seeing every page that carries one.
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

        A heading the model never answers for is left without a level rather
        than guessed at, since the export already handles one.

        Args:
            all_page_images: Every page of the document, as scanned, 0-indexed.
                Only the pages holding a heading are shown to the model.
            processing_blocks: Every block of the document, in current order,
                as the Classifier left them.
        """
        headings = _collect_headings(processing_blocks)

        if not headings:
            logger.info("leveler | the document holds no heading")
            return

        messages = self._build_messages(all_page_images, headings)

        for attempt in range(1, MAX_ATTEMPT_COUNT + 1):
            heading_levels = self._request_levels(messages, attempt)
            messages.append(AIMessage(content=heading_levels.model_dump_json()))

            problems = _apply_levels(heading_levels, headings)
            unleveled = [
                heading for heading in headings if heading.heading_level is None
            ]

            if not problems and not unleveled:
                logger.info("leveler | %d heading(s) leveled", len(headings))
                return

            logger.warning(
                "leveler | attempt %d left %d heading(s) unleveled",
                attempt,
                len(unleveled),
            )
            messages.append(HumanMessage(content=_retry_message(problems, unleveled)))

        logger.warning(
            "leveler | gave up after %d attempts; %d heading(s) have no level",
            MAX_ATTEMPT_COUNT,
            len([heading for heading in headings if heading.heading_level is None]),
        )

    def _request_levels(
        self,
        messages: list[BaseMessage],
        attempt: int,
    ) -> HeadingLevels:
        """Asks the model for the level of every heading."""
        heading_levels = self.leveler_model.invoke(messages)

        if not isinstance(heading_levels, HeadingLevels):
            raise RuntimeError("The leveler model returned no heading levels.")

        logger.info(
            "leveler | attempt %d: %d level(s)", attempt, len(heading_levels.levels)
        )

        return heading_levels

    def _build_messages(
        self,
        all_page_images: list[Image],
        headings: list[ProcessingBlockTextHeading],
    ) -> list[BaseMessage]:
        """The system prompt plus every heading page and the headings' text."""
        content: list[dict] = []

        # one image per page holding a heading, in page order
        for page_index, page_headings in _group_by_page(headings):
            named = "heading block" if len(page_headings) == 1 else "heading blocks"
            content += build_image_message(
                f"Page {page_index + 1}, holding {named} {_list_ids(page_headings)}:",
                pil_to_base64(all_page_images[page_index]),
            )

        content.append(create_text_block(_headings_text(headings)))

        return [
            SystemMessage(content=LEVELER_SYSTEM_PROMPT),
            HumanMessage(content=content),
        ]


def _collect_headings(
    processing_blocks: list[ProcessingBlock],
) -> list[ProcessingBlockTextHeading]:
    """Every heading of the document, in document order."""
    return [
        block
        for block in processing_blocks
        if isinstance(block, ProcessingBlockTextHeading)
    ]


def _group_by_page(
    headings: list[ProcessingBlockTextHeading],
) -> list[tuple[int, list[ProcessingBlockTextHeading]]]:
    """The headings grouped by the page they are on, in page order."""
    grouped: dict[int, list[ProcessingBlockTextHeading]] = {}

    for heading in headings:
        grouped.setdefault(heading.page_index, []).append(heading)

    return sorted(grouped.items())


def _headings_text(headings: list[ProcessingBlockTextHeading]) -> str:
    """Every heading as JSON, in document order, as the model sees them."""
    listed = [
        {
            "block_id": heading.block_id,
            "page_number": heading.page_index + 1,
            "text": heading.text,
        }
        for heading in headings
    ]

    return (
        "The headings of the document, in the order they are read in:\n"
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
                "were given, so it was ignored."
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
