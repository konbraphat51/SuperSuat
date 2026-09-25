"""Transcribing one page into Markdown with a multimodal chat model."""

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
from ..Markers import without_page_markers
from ..MarkdownValidator import validate_page_output
from ..Schema import DetectedFigure, PageTask
from .prompt import PROMPT

logger = logging.getLogger(__name__)

# A message's content, as HumanMessage takes it.
Content = list[str | dict[Any, Any]]

# Guard against a model that keeps returning Markdown that does not check out.
MAX_ATTEMPT_COUNT = 3


class PageTranscriber:
    """Writes one page out as Markdown per request.

    Every answer is checked against what the page was asked for - its
    figures and its continuation markers - and a failing one is sent back
    with what is wrong, so a page either comes back whole or stops the run.
    Every request carries the page's index and kind in its run metadata, so
    a callback can tell what each request cost."""

    def __init__(
        self,
        model: BaseChatModel,
        max_attempt_count: int = MAX_ATTEMPT_COUNT,
    ) -> None:
        """
        Args:
            model: Multimodal chat model that writes the Markdown.
            max_attempt_count: Most answers asked for per page.
        """
        self.model = model
        self.max_attempt_count = max_attempt_count

    def transcribe(
        self,
        task: PageTask,
        rendered_pages: Sequence[Image],
        figures: Sequence[DetectedFigure],
    ) -> str:
        """The Markdown of a page, continuation markers included.

        Args:
            task: The page to write.
            rendered_pages: Every page of the document, its figures drawn on.
            figures: Every figure of the document.

        Raises:
            RuntimeError: No answer checked out in max_attempt_count attempts.
        """
        content: Content = [
            *build_image_message(
                f"{_page_label(task, figures)}:",
                page_to_base64(rendered_pages[task.page_index]),
            )
        ]

        return self._transcribe(
            task,
            [SystemMessage(content=PROMPT), HumanMessage(content=content)],
            figures,
        )

    def _transcribe(
        self,
        task: PageTask,
        messages: list[BaseMessage],
        figures: Sequence[DetectedFigure],
    ) -> str:
        """Asks for the page's Markdown until an answer checks out."""
        label = f"page {task.page_index}"
        figure_ids = _figure_ids(task.page_index, figures)
        metadata = {"page_index": task.page_index, "page_kind": "write"}

        for attempt in range(1, self.max_attempt_count + 1):
            response = self.model.invoke(messages, config={"metadata": metadata})
            log_agent_message(f"{label} attempt {attempt}", response)

            # the stitcher places the page markers, so any the model wrote go
            markdown = without_page_markers(
                strip_code_fence(response.text.strip())
            ).strip()
            problems = validate_page_output(markdown, figure_ids)

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


def _figure_ids(page_index: int, figures: Sequence[DetectedFigure]) -> list[int]:
    """The ids of the figures on the given page."""
    return [figure.block_id for figure in figures if figure.page_index == page_index]


def _page_label(task: PageTask, figures: Sequence[DetectedFigure]) -> str:
    """What a page image is introduced with: where it is, and its figures."""
    ids = _figure_ids(task.page_index, figures)
    place = f"Page {task.page_index + 1} of {task.page_count}"

    if not ids:
        return f"{place} (no figures)"

    return f"{place} (figures {', '.join(str(i) for i in ids)})"


def _retry_message(problems: list[str]) -> str:
    """What the model is told when its answer did not check out."""
    return (
        "Your Markdown cannot be used as it is. Write the whole of it again, "
        "fixing these problems:\n" + "\n".join(f"- {problem}" for problem in problems)
    )
