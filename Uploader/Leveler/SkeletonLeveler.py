"""Laying out a document's heading hierarchy from its text and tables of contents alone."""

import logging
from dataclasses import dataclass

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from OcrModule.OcrSchema import OcrResultBlockTableOfContents

from .Headings import Heading, headings_json
from .LevelerSchema import SkeletonLevels
from .LevelRequest import request_levels
from .prompt import SKELETON_SYSTEM_PROMPT
from .TableOfContentsText import table_of_contents_text

logger = logging.getLogger(__name__)

# Headings past which one skeleton request grows long; logged, not yet split.
MAX_HEADINGS_PER_SKELETON = 600


@dataclass
class Skeleton:
    """Every heading's level as judged from text, and those it did not settle.

    Attributes:
        levels: The level of every heading, keyed by block_index.
        uncertain: The block_index of each heading whose page has to decide it.
    """

    levels: dict[int, float]
    uncertain: set[int]


class SkeletonLeveler:
    """Gives every heading a level from its text and the document's tables of
    contents, in one request without page images, and marks the headings the
    text leaves open."""

    def __init__(
        self,
        leveler_model: BaseChatModel,
    ) -> None:
        """
        Args:
            leveler_model: Chat model that lays out the hierarchy.
        """
        self.skeleton_model = leveler_model.with_structured_output(SkeletonLevels)

    def level(
        self,
        headings: list[Heading],
        tables_of_contents: list[OcrResultBlockTableOfContents],
    ) -> Skeleton:
        """The level of every heading, and which of them need their page.

        Args:
            headings: Every heading of the document, in document order.
            tables_of_contents: Every table of contents printed in it.

        Raises:
            RuntimeError: A heading was still left without a level after
                MAX_ATTEMPT_COUNT attempts.
        """
        if len(headings) > MAX_HEADINGS_PER_SKELETON:
            logger.warning(
                "Skeleton leveler | %d headings in one request, over %d",
                len(headings),
                MAX_HEADINGS_PER_SKELETON,
            )

        levels: dict[int, float] = {}
        answers = request_levels(
            model=self.skeleton_model,
            answer_type=SkeletonLevels,
            messages=_build_messages(headings, tables_of_contents),
            headings=headings,
            levels=levels,
            label="skeleton",
        )

        # a later answer about the same heading stands over an earlier one
        needs_page = {
            level.target_block_id: level.needs_page_image
            for answer in answers
            for level in answer.levels
            if level.target_block_id in levels
        }
        uncertain = {block_id for block_id, needed in needs_page.items() if needed}

        logger.info(
            "Skeleton leveler | %d heading(s), %d need their page",
            len(headings),
            len(uncertain),
        )

        return Skeleton(levels=levels, uncertain=uncertain)


def _build_messages(
    headings: list[Heading],
    tables_of_contents: list[OcrResultBlockTableOfContents],
) -> list[BaseMessage]:
    """The system prompt, the tables of contents, and every heading as JSON."""
    contents_text = table_of_contents_text(tables_of_contents)
    contents = (
        "The tables of contents printed in the document, each entry as "
        f"`number | title | page`:\n{contents_text}"
        if contents_text
        else "The document has no table of contents."
    )

    return [
        SystemMessage(content=SKELETON_SYSTEM_PROMPT),
        HumanMessage(
            content=f"{contents}\n\nEvery heading of the document, in the order "
            f"they are read in:\n{headings_json(headings, None)}"
        ),
    ]
