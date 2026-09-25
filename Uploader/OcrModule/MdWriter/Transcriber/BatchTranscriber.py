"""Transcribing a batch of pages into Markdown with a multimodal chat model."""

import logging
from collections.abc import Sequence
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from PIL.Image import Image

from ...LlmHelper import (
    build_image_message,
    log_agent_message,
    page_to_base64,
    strip_code_fence,
)
from ..Markers import page_marker
from ..MarkdownValidator import validate_batch_output
from ..Schema import DetectedFigure, PageBatch
from .prompt import FILL_PROMPT, WRITE_PROMPT

logger = logging.getLogger(__name__)

# A message's content, as HumanMessage takes it.
Content = list[str | dict[Any, Any]]

# Guard against a model that keeps returning Markdown that does not check out.
MAX_ATTEMPT_COUNT = 3


class BatchTranscriber:
    """Writes the pages of one batch out as Markdown.

    Every answer is checked against what the batch was asked for - its page
    markers and its figures - and a failing one is sent back with what is
    wrong, so a batch either comes back whole or stops the run."""

    def __init__(
        self,
        model: BaseChatModel,
        max_attempt_count: int = MAX_ATTEMPT_COUNT,
    ) -> None:
        """
        Args:
            model: Multimodal chat model that writes the Markdown.
            max_attempt_count: Most answers asked for per batch.
        """
        self.model = model
        self.max_attempt_count = max_attempt_count

    def write(
        self,
        batch: PageBatch,
        rendered_pages: Sequence[Image],
        figures: Sequence[DetectedFigure],
    ) -> str:
        """The Markdown of every page of a write batch.

        Args:
            batch: The batch to write.
            rendered_pages: Every page of the document, its figures drawn on.
            figures: Every figure of the document.

        Raises:
            RuntimeError: No answer checked out in max_attempt_count attempts.
        """
        content: Content = [
            _text_block(
                f"Transcribe pages {batch.first_page} to {batch.last_page}. "
                "Each page image is preceded by its page number."
            )
        ]

        for page_index in batch.pages:
            content += build_image_message(
                f"{_page_label(page_index, figures)}:",
                page_to_base64(rendered_pages[page_index]),
            )

        content.append(_text_block(_markers_reminder(batch)))

        return self._transcribe(
            batch,
            [SystemMessage(content=WRITE_PROMPT), HumanMessage(content=content)],
            figures,
            has_next=False,
        )

    def fill(
        self,
        batch: PageBatch,
        rendered_pages: Sequence[Image],
        figures: Sequence[DetectedFigure],
        previous_markdown: str,
        next_markdown: str | None,
    ) -> str:
        """The Markdown of the inner pages of a fill batch, written to join
        the parts either side of it into one text.

        Args:
            batch: The batch to fill.
            rendered_pages: Every page of the document, its figures drawn on.
            figures: Every figure of the document.
            previous_markdown: What the write batch before this one returned.
            next_markdown: What the write batch after this one returned, or
                None if this batch ends the document.

        Raises:
            RuntimeError: No answer checked out in max_attempt_count attempts.
        """
        written = ", ".join(str(page) for page in batch.written_pages)
        content: Content = [
            _text_block(f"<previous_part>\n{previous_markdown}\n</previous_part>"),
            _text_block(
                f"Your part: pages {batch.first_page} to {batch.last_page}. "
                f"Transcribe pages {written} only. Each page image is preceded "
                "by its page number."
            ),
        ]

        for page_index in batch.pages:
            role = (
                "to transcribe"
                if page_index in batch.written_pages
                else "already transcribed, context only"
            )
            content += build_image_message(
                f"{_page_label(page_index, figures)}, {role}:",
                page_to_base64(rendered_pages[page_index]),
            )

        if next_markdown is not None:
            content.append(_text_block(f"<next_part>\n{next_markdown}\n</next_part>"))

        content.append(_text_block(_markers_reminder(batch)))

        return self._transcribe(
            batch,
            [SystemMessage(content=FILL_PROMPT), HumanMessage(content=content)],
            figures,
            has_next=next_markdown is not None,
        )

    def _transcribe(
        self,
        batch: PageBatch,
        messages: list[BaseMessage],
        figures: Sequence[DetectedFigure],
        has_next: bool,
    ) -> str:
        """Asks for the batch's Markdown until an answer checks out."""
        label = f"batch {batch.index} (pages {batch.first_page}-{batch.last_page})"
        figure_ids = _figure_ids(batch.written_pages, figures)

        for attempt in range(1, self.max_attempt_count + 1):
            response = self.model.invoke(messages)
            log_agent_message(f"{label} attempt {attempt}", response)

            markdown = strip_code_fence(response.text.strip())
            problems = validate_batch_output(markdown, batch, figure_ids, has_next)

            if not problems:
                return markdown

            logger.warning(
                "%s attempt %d: %d problem(s): %s",
                label,
                attempt,
                len(problems),
                problems,
            )
            messages += [
                AIMessage(content=markdown),
                HumanMessage(content=_retry_message(problems)),
            ]

        raise RuntimeError(
            f"{label} did not return usable Markdown in "
            f"{self.max_attempt_count} attempts."
        )


def _text_block(text: str) -> dict[Any, Any]:
    """A standard text content block."""
    return {"type": "text", "text": text}


def _figure_ids(
    pages: Sequence[int],
    figures: Sequence[DetectedFigure],
) -> list[int]:
    """The ids of the figures on the given pages."""
    return [figure.block_id for figure in figures if figure.page_index in pages]


def _page_label(page_index: int, figures: Sequence[DetectedFigure]) -> str:
    """What a page image is introduced with: its number and its figures."""
    ids = _figure_ids([page_index], figures)

    if not ids:
        return f"Page {page_index} (no figures)"

    return f"Page {page_index} (figures {', '.join(str(i) for i in ids)})"


def _markers_reminder(batch: PageBatch) -> str:
    """The page markers the answer has to carry, spelled out."""
    markers = ", ".join(page_marker(page) for page in batch.written_pages)
    return f"Write these page markers, once each and in this order: {markers}."


def _retry_message(problems: list[str]) -> str:
    """What the model is told when its answer did not check out."""
    return (
        "Your Markdown cannot be used as it is. Write the whole of it again, "
        "fixing these problems:\n" + "\n".join(f"- {problem}" for problem in problems)
    )
