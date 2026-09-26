"""Transcribing one page into Markdown with a multimodal chat model."""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.runnables import Runnable

from ...LlmHelper import (
    MODEL_IMAGE_MAX_EDGE,
    build_image_message,
    log_agent_message,
    page_to_base64,
    strip_code_fence,
)
from .Agreement import agreement, letter_count
from .BlankPage import BlankPageDetector
from ..FigureBoard import FigureBoard
from ..FigureCorrector.FigureCorrectionTool import (
    CorrectionSession,
    FigureCorrectionTool,
)
from ..Syntax.Markers import is_blank_page, without_page_markers
from .MarkdownValidator import validate_page_output
from ..Schema import PageTask
from .prompt import build_prompt

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
    whichever answer agrees more. A page with neither figures nor ink is
    written as empty without asking the model at all, as is one the model
    answers holds nothing to transcribe. Every request carries the page's index and
    kind in its run metadata, so a callback can tell what each request cost.

    With a figure correction tool, the model may have its page's figure boxes
    redrawn when the detector got them wrong: the call corrects them on the
    board at once, the page is shown again with the new boxes, and the answer is
    checked against the figures as they are then. A tool round is not an
    attempt, unless the page keeps calling past its limit."""

    def __init__(
        self,
        model: BaseChatModel,
        max_attempt_count: int = MAX_ATTEMPT_COUNT,
        image_max_edge: int = MODEL_IMAGE_MAX_EDGE,
        escalation: Escalation | None = None,
        blank_page_detector: BlankPageDetector | None = None,
        figure_correction: FigureCorrectionTool | None = None,
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
            blank_page_detector: Tells the blank pages, which the model is
                not asked to write.
            figure_correction: The tool the model has wrong figure boxes
                redrawn with, if any; the model must support tool calling.
        """
        self.model = model
        self.max_attempt_count = max_attempt_count
        self.image_max_edge = image_max_edge
        self.escalation = escalation
        self.blank_page_detector = blank_page_detector or BlankPageDetector()
        self.figure_correction = figure_correction

    def transcribe(
        self,
        task: PageTask,
        board: FigureBoard,
        reference: str | None = None,
    ) -> str:
        """The Markdown of a page, continuation markers included.

        Args:
            task: The page to write.
            board: Every page of the document and its figures.
            reference: The page's text as a conventional OCR read it, if any.

        Raises:
            RuntimeError: No answer checked out in max_attempt_count attempts.
        """
        if not board.figure_ids_on(task.page_index) and (
            self.blank_page_detector.is_blank(board.page(task.page_index))
        ):
            logger.info("page %d is blank; not sent to the model", task.page_index)
            return ""

        markdown = self._transcribe(self.model, "write", task, board, reference)

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
            self.escalation.model, "escalate", task, board, reference
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
        board: FigureBoard,
        reference: str | None,
    ) -> str:
        """Asks `model` for the page's Markdown until an answer checks out."""
        label = f"page {task.page_index} ({kind})"
        messages = self._first_messages(task, board, reference)
        metadata = {"page_index": task.page_index, "page_kind": kind}

        session = (
            self.figure_correction.session(task.page_index, board)
            if self.figure_correction is not None
            else None
        )
        runnable: Runnable[LanguageModelInput, AIMessage] = (
            model.bind_tools([self.figure_correction.definition])
            if self.figure_correction is not None
            else model
        )

        attempt = 0
        while attempt < self.max_attempt_count:
            response = runnable.invoke(messages, config={"metadata": metadata})
            log_agent_message(f"{label} attempt {attempt + 1}", response)

            if session is not None and response.tool_calls:
                # a page that keeps calling past its limit spends its attempts
                if session.exhausted:
                    attempt += 1
                messages += self._run_tool_calls(session, response, task, board, label)
                continue
            attempt += 1

            # the stitcher places the page markers, so any the model wrote go
            markdown = without_page_markers(
                strip_code_fence(response.text.strip())
            ).strip()
            problems = validate_page_output(
                markdown, board.figure_ids_on(task.page_index)
            )

            if not problems:
                # a page the model found nothing on is written as empty
                return "" if is_blank_page(markdown) else markdown

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

    def _run_tool_calls(
        self,
        session: CorrectionSession,
        response: AIMessage,
        task: PageTask,
        board: FigureBoard,
        label: str,
    ) -> list[BaseMessage]:
        """The model's tool calls with their results, and the page drawn again
        if they changed its figures."""
        messages: list[BaseMessage] = [response]
        changed = False

        for tool_call in response.tool_calls:
            outcome = session.call(tool_call["name"], tool_call["args"])
            result = ToolMessage(
                content=outcome.message,
                tool_call_id=tool_call["id"] or "",
                name=tool_call["name"],
            )
            log_agent_message(label, result)
            messages.append(result)
            changed = changed or outcome.changed

        if changed:
            messages.append(HumanMessage(content=self._page_content(task, board)))
        return messages

    def _first_messages(
        self, task: PageTask, board: FigureBoard, reference: str | None
    ) -> list[BaseMessage]:
        """The instructions and the page, as the page stands on the board now."""
        content = self._page_content(task, board)
        if reference is not None:
            content.append(
                {
                    "type": "text",
                    "text": f"<reference_ocr>\n{reference}\n</reference_ocr>",
                }
            )

        prompt = build_prompt(
            reference=reference is not None,
            figure_correction=self.figure_correction is not None,
        )
        return [SystemMessage(content=prompt), HumanMessage(content=content)]

    def _page_content(self, task: PageTask, board: FigureBoard) -> Content:
        """The page image with its figures drawn on, introduced by its label."""
        return [
            *build_image_message(
                f"{_page_label(task, board.figure_ids_on(task.page_index))}:",
                page_to_base64(board.rendered(task.page_index), self.image_max_edge),
            )
        ]


def _page_label(task: PageTask, ids: Sequence[int]) -> str:
    """What a page image is introduced with: where it is, and its figures."""
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
