"""Redrawing the figure boxes of one page with a grounding vision model, as asked."""

import json
import logging
from collections.abc import Collection, Sequence
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from ...LlmHelper import (
    MODEL_IMAGE_MAX_EDGE,
    build_image_message,
    log_agent_message,
    page_to_base64,
    strip_code_fence,
)
from ..FigureBoard import FigureBoard
from ..Schema import CorrectedFigure, DetectedFigure
from .prompt import CORRECTION_PROMPT

logger = logging.getLogger(__name__)

# Guard against a model that keeps answering boxes that do not check out.
MAX_ATTEMPT_COUNT = 3

# What the coordinates are scaled to, as Qwen3-VL grounds them: 0-1000 of each side.
NORMALIZED_EXTENT = 1000

# The kind a correction's requests carry in their run metadata.
PAGE_KIND = "correct-figures"

Box = tuple[int, int, int, int]


class FigureCorrector:
    """Asks a grounding vision model for a page's figure boxes, corrected as told.

    Built for Qwen3-VL (such as on Amazon Bedrock), which grounds boxes as
    `bbox_2d` [x1, y1, x2, y2] scaled to 0-1000 of the image. The model is
    shown the page with its current boxes and as scanned, and answers every
    figure of the page; an answer that does not check out is sent back with
    what is wrong."""

    def __init__(
        self,
        model: BaseChatModel,
        max_attempt_count: int = MAX_ATTEMPT_COUNT,
        image_max_edge: int = MODEL_IMAGE_MAX_EDGE,
    ) -> None:
        """
        Args:
            model: Multimodal chat model that grounds the boxes.
            max_attempt_count: Most answers asked for per correction.
            image_max_edge: Longest side the page is sent at.
        """
        self.model = model
        self.max_attempt_count = max_attempt_count
        self.image_max_edge = image_max_edge

    def correct(
        self, page_index: int, board: FigureBoard, instruction: str
    ) -> list[CorrectedFigure]:
        """Every figure of the page, its boxes redrawn as `instruction` asks.

        Nothing is changed on the board: applying the answer is the caller's.

        Args:
            page_index: The page whose figures are corrected.
            board: Every page of the document and its figures.
            instruction: What is wrong with the boxes, in the words of the
                model writing the page.

        Raises:
            RuntimeError: No answer checked out in max_attempt_count attempts.
        """
        label = f"page {page_index} (correct figures)"
        figures = board.figures_on(page_index)
        size = board.page(page_index).size
        messages = self._first_messages(page_index, board, figures, instruction)
        metadata = {"page_index": page_index, "page_kind": PAGE_KIND}

        for attempt in range(1, self.max_attempt_count + 1):
            response = self.model.invoke(messages, config={"metadata": metadata})
            log_agent_message(f"{label} attempt {attempt}", response)

            answer = response.text.strip()
            corrections, problems = parse_corrections(
                answer, [figure.block_id for figure in figures], size
            )
            if not problems:
                return corrections

            logger.warning("%s attempt %d: %s", label, attempt, problems)
            messages += [
                AIMessage(content=answer),
                HumanMessage(content=_retry_message(problems)),
            ]

        raise RuntimeError(
            f"{label} did not return usable boxes in {self.max_attempt_count} attempts."
        )

    def _first_messages(
        self,
        page_index: int,
        board: FigureBoard,
        figures: Sequence[DetectedFigure],
        instruction: str,
    ) -> list[BaseMessage]:
        """The instructions, the page twice, its current boxes and the request."""
        size = board.page(page_index).size
        current = [
            {"id": figure.block_id, "bbox_2d": to_normalized(figure.bounding_box, size)}
            for figure in figures
        ]
        content: list[str | dict[Any, Any]] = [
            *build_image_message(
                "The page with its current figure boxes, each labeled with its id:",
                page_to_base64(board.rendered(page_index), self.image_max_edge),
            ),
            *build_image_message(
                "The same page as scanned, which the coordinates are on:",
                page_to_base64(board.page(page_index), self.image_max_edge),
            ),
            {
                "type": "text",
                "text": (
                    f"<current_figures>\n{json.dumps(current)}\n</current_figures>\n"
                    f"<request>\n{instruction}\n</request>"
                ),
            },
        ]
        return [SystemMessage(content=CORRECTION_PROMPT), HumanMessage(content=content)]


def parse_corrections(
    answer: str, figure_ids: Collection[int], size: tuple[int, int]
) -> tuple[list[CorrectedFigure], list[str]]:
    """The figures a grounding model's answer lists, and what is wrong with it.

    Args:
        answer: The model's answer, the JSON of the prompt.
        figure_ids: The ids of the page's current figures.
        size: The page's (width, height) in pixels, which the boxes are scaled to.

    Returns:
        The corrected figures, and one line per problem for the model; the
        figures are only of use when there are no problems.
    """
    items, problems = _figure_items(answer)
    corrections: list[CorrectedFigure] = []
    seen_ids: set[int] = set()

    for index, item in enumerate(items):
        where = f"Figure entry {index + 1}"
        if not isinstance(item, dict):
            problems.append(f"{where} is not an object with an id and a bbox_2d.")
            continue

        block_id = item.get("id")
        if block_id is not None and (
            isinstance(block_id, bool)
            or not isinstance(block_id, int)
            or block_id not in figure_ids
        ):
            problems.append(
                f"{where} has id {block_id!r}, which is no current box; "
                "give null for a figure that had no box."
            )
            continue
        if block_id is not None and block_id in seen_ids:
            problems.append(f"{where} repeats id {block_id}; give each id once.")
            continue

        box = _pixel_box(item.get("bbox_2d"), size)
        if box is None:
            problems.append(
                f"{where} needs a bbox_2d of four numbers [x1, y1, x2, y2] from 0 "
                "to 1000, with x1 < x2 and y1 < y2."
            )
            continue

        if block_id is not None:
            seen_ids.add(block_id)
        corrections.append(CorrectedFigure(block_id, box))

    return corrections, problems


def to_normalized(box: Box, size: tuple[int, int]) -> list[int]:
    """An (x, y, width, height) pixel box as [x1, y1, x2, y2] scaled to 0-1000."""
    x, y, width, height = box
    page_width, page_height = size
    return [
        round(x * NORMALIZED_EXTENT / page_width),
        round(y * NORMALIZED_EXTENT / page_height),
        round((x + width) * NORMALIZED_EXTENT / page_width),
        round((y + height) * NORMALIZED_EXTENT / page_height),
    ]


def _figure_items(answer: str) -> tuple[list[Any], list[str]]:
    """The entries of the answer's "figures" list, or the problem reading it."""
    text = strip_code_fence(answer)
    start, end = text.find("{"), text.rfind("}")

    try:
        parsed = json.loads(text[start : end + 1]) if start >= 0 else None
    except json.JSONDecodeError:
        parsed = None

    if not isinstance(parsed, dict) or not isinstance(parsed.get("figures"), list):
        return [], ['Answer with the JSON object {"figures": [...]} and nothing else.']

    return list(parsed["figures"]), []


def _pixel_box(value: Any, size: tuple[int, int]) -> Box | None:
    """A [x1, y1, x2, y2] box scaled to 0-1000 as an (x, y, width, height)
    pixel box, or None if it is no box; a corner off the page is moved onto it."""
    if not isinstance(value, list) or len(value) != 4:
        return None
    if any(isinstance(v, bool) or not isinstance(v, int | float) for v in value):
        return None

    page_width, page_height = size
    x1, y1, x2, y2 = (min(max(float(v), 0.0), NORMALIZED_EXTENT) for v in value)
    left = round(x1 * page_width / NORMALIZED_EXTENT)
    top = round(y1 * page_height / NORMALIZED_EXTENT)
    right = round(x2 * page_width / NORMALIZED_EXTENT)
    bottom = round(y2 * page_height / NORMALIZED_EXTENT)

    if right <= left or bottom <= top:
        return None
    return (left, top, right - left, bottom - top)


def _retry_message(problems: list[str]) -> str:
    """What the model is told when its answer did not check out."""
    return (
        "Your answer cannot be used as it is. Answer the whole JSON again, "
        "fixing these problems:\n" + "\n".join(f"- {problem}" for problem in problems)
    )
