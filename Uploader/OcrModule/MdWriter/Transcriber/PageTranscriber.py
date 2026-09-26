"""Transcribing one page into Markdown with a multimodal chat model."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from PIL.Image import Image

from ...LlmHelper import (
    MODEL_IMAGE_MAX_EDGE,
    build_image_message,
    log_agent_message,
    page_to_base64,
    strip_code_fence,
)
from ..Agreement import agreement, letter_count
from ..Syntax.Markers import without_page_markers
from ..MarkdownValidator import validate_page_output
from ..Schema import DetectedFigure, PageTask
from .prompt import PROMPT, PROMPT_WITH_REFERENCE

logger = logging.getLogger(__name__)

# A message's content, as HumanMessage takes it.
Content = list[str | dict[Any, Any]]

# Guard against a model that keeps returning Markdown that does not check out.
MAX_ATTEMPT_COUNT = 3

# Agreement with the reference below which a page is taken as misread.
DEFAULT_MIN_AGREEMENT = 0.95

# Shortest reference, in letters, the agreement with says anything: a page of
# figures, whose reference is a caption or a side tab, is never escalated.
DEFAULT_MIN_REFERENCE_LETTERS = 200


@dataclass(frozen=True)
class Escalation:
    """A stronger model a page is written again with when it looks misread.

    Attributes:
        model: The multimodal chat model the page is written again with.
        min_agreement: The agreement with the reference text below which the
            first answer is taken as misread (see Agreement.agreement).
        min_reference_letters: The fewest letters a reference has for the
            agreement with it to count.
    """

    model: BaseChatModel
    min_agreement: float = DEFAULT_MIN_AGREEMENT
    min_reference_letters: int = DEFAULT_MIN_REFERENCE_LETTERS


class PageTranscriber:
    """Writes one page out as Markdown per request.

    Every answer is checked against what the page was asked for - its
    figures and its continuation markers - and a failing one is sent back
    with what is wrong, so a page either comes back whole or stops the run.

    Given a page's reference text, the model is shown it to check the
    characters it writes; and with an escalation, a page whose answer agrees
    too little with it is written again by the stronger model, keeping
    whichever answer agrees more. Every request carries the page's index and
    kind in its run metadata, so a callback can tell what each request cost."""

    def __init__(
        self,
        model: BaseChatModel,
        max_attempt_count: int = MAX_ATTEMPT_COUNT,
        image_max_edge: int = MODEL_IMAGE_MAX_EDGE,
        escalation: Escalation | None = None,
    ) -> None:
        """
        Args:
            model: Multimodal chat model that writes the Markdown.
            max_attempt_count: Most answers asked for per page.
            image_max_edge: Longest side a page is sent at. A model that reads
                every pixel it is sent sees small print better at a larger
                size, for more input tokens.
            escalation: The model a misread page is written again with, if
                any; only used for a page given a reference.
        """
        self.model = model
        self.max_attempt_count = max_attempt_count
        self.image_max_edge = image_max_edge
        self.escalation = escalation

    def transcribe(
        self,
        task: PageTask,
        rendered_pages: Sequence[Image],
        figures: Sequence[DetectedFigure],
        reference: str | None = None,
    ) -> str:
        """The Markdown of a page, continuation markers included.

        Args:
            task: The page to write.
            rendered_pages: Every page of the document, its figures drawn on.
            figures: Every figure of the document.
            reference: The page's text as a conventional OCR read it, if any.

        Raises:
            RuntimeError: No answer checked out in max_attempt_count attempts.
        """
        content: Content = [
            *build_image_message(
                f"{_page_label(task, figures)}:",
                page_to_base64(rendered_pages[task.page_index], self.image_max_edge),
            )
        ]
        if reference is not None:
            content.append(
                {
                    "type": "text",
                    "text": f"<reference_ocr>\n{reference}\n</reference_ocr>",
                }
            )

        prompt = PROMPT if reference is None else PROMPT_WITH_REFERENCE
        messages: list[BaseMessage] = [
            SystemMessage(content=prompt),
            HumanMessage(content=content),
        ]
        markdown = self._transcribe(self.model, "write", task, list(messages), figures)

        if (
            reference is None
            or self.escalation is None
            or letter_count(reference) < self.escalation.min_reference_letters
        ):
            return markdown

        score = agreement(markdown, reference)
        if score >= self.escalation.min_agreement:
            return markdown

        escalated = self._transcribe(
            self.escalation.model, "escalate", task, list(messages), figures
        )
        escalated_score = agreement(escalated, reference)
        logger.info(
            "page %d escalated: agreement %.3f -> %.3f",
            task.page_index,
            score,
            escalated_score,
        )
        return escalated if escalated_score >= score else markdown

    def _transcribe(
        self,
        model: BaseChatModel,
        kind: str,
        task: PageTask,
        messages: list[BaseMessage],
        figures: Sequence[DetectedFigure],
    ) -> str:
        """Asks `model` for the page's Markdown until an answer checks out."""
        label = f"page {task.page_index} ({kind})"
        figure_ids = _figure_ids(task.page_index, figures)
        metadata = {"page_index": task.page_index, "page_kind": kind}

        for attempt in range(1, self.max_attempt_count + 1):
            response = model.invoke(messages, config={"metadata": metadata})
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
