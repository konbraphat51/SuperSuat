"""Deciding, at every page turn, whether the two pages share a paragraph."""

import logging
from collections.abc import Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from ...LlmHelper import log_agent_message
from ..Syntax.Containers import (
    TABLE_OF_CONTENTS_CONTAINER,
    closing_container,
    opening_container,
)
from ..Syntax.Markers import FIGURE_REFERENCE_PATTERN, ContinuationSplit
from ..Transcriber.prompt import JOIN_PROMPT

logger = logging.getLogger(__name__)

# What a paragraph that ends at a sentence's end, rather than in its middle, ends with.
SENTENCE_ENDINGS = "。．.!?！？」』）)"

# How much of each side of a page turn the judge is shown.
JUDGED_LENGTH = 300

# What separates two paragraphs.
PARAGRAPH_BREAK = "\n\n"


class JoinJudge:
    """Asks a chat model, from the text alone, whether a page turn splits a paragraph.

    Only consulted where the two pages disagree, so the text on either side
    is all it needs."""

    def __init__(self, model: BaseChatModel) -> None:
        """
        Args:
            model: The chat model asked; a small one is enough.
        """
        self.model = model

    def judge(self, page_index: int, end_of_page: str, start_of_next: str) -> bool:
        """Whether the next page's first paragraph continues this page's last one.

        Args:
            page_index: The page the turn follows, for the log and the usage.
            end_of_page: The last paragraph of the page.
            start_of_next: The first paragraph of the next page.
        """
        messages = [
            SystemMessage(content=JOIN_PROMPT),
            HumanMessage(
                content=(
                    f"<end_of_page>\n{end_of_page[-JUDGED_LENGTH:]}\n</end_of_page>\n"
                    f"<start_of_next_page>\n{start_of_next[:JUDGED_LENGTH]}\n"
                    "</start_of_next_page>"
                )
            ),
        ]
        response = self.model.invoke(
            messages,
            config={"metadata": {"page_index": page_index, "page_kind": "join"}},
        )
        log_agent_message(f"join after page {page_index}", response)

        return response.text.strip().lower().startswith("join")


def decide_joins(
    pages: Sequence[ContinuationSplit],
    judge: JoinJudge | None = None,
) -> list[bool]:
    """Whether each page's last paragraph runs on into the next page's first.

    Each page says so of its own ends. Where the two pages of a turn agree,
    that is the answer; where they disagree, the judge decides, or without
    one, whether the page's last paragraph stops at a sentence's end.

    Args:
        pages: Every page's Markdown, its continuation markers split off.
        judge: What settles a turn the two pages disagree on, if anything.
    """
    joins: list[bool] = []

    for index, (page, following) in enumerate(zip(pages, pages[1:])):
        end = _last_paragraph(page.body)
        start = _first_paragraph(following.body)

        if not _is_text(end) or not _is_text(start):
            joins.append(False)
        # a table of contents over a turn is two blocks the parser merges, never one paragraph
        elif _is_table_of_contents_turn(page.body, following.body):
            joins.append(False)
        elif page.continued_by_next == following.continues_previous:
            joins.append(page.continued_by_next)
        elif judge is not None:
            joins.append(judge.judge(index, end, start))
        else:
            joins.append(not end.rstrip().endswith(tuple(SENTENCE_ENDINGS)))

        logger.info(
            "page %d -> %d | marked %s / %s, %s",
            index,
            index + 1,
            page.continued_by_next,
            following.continues_previous,
            "join" if joins[-1] else "break",
        )

    return joins


def _last_paragraph(body: str) -> str:
    """The page's last paragraph, past any figure the stitcher moves aside."""
    paragraphs = _paragraphs(body)
    return paragraphs[-1] if paragraphs else ""


def _first_paragraph(body: str) -> str:
    """The page's first paragraph, past any figure the stitcher moves aside."""
    paragraphs = _paragraphs(body)
    return paragraphs[0] if paragraphs else ""


def _paragraphs(body: str) -> list[str]:
    """The page's paragraphs, figures left out."""
    return [
        paragraph.strip()
        for paragraph in body.strip().split(PARAGRAPH_BREAK)
        if paragraph.strip()
        and not FIGURE_REFERENCE_PATTERN.fullmatch(paragraph.strip())
    ]


def _is_table_of_contents_turn(body: str, following_body: str) -> bool:
    """Whether the page ends with a table of contents block or the next starts with one."""
    return TABLE_OF_CONTENTS_CONTAINER in (
        closing_container(body),
        opening_container(following_body),
    )


def _is_text(paragraph: str) -> bool:
    """Whether a paragraph is running text, which a page turn may split."""
    return bool(paragraph) and not paragraph.startswith("#")
