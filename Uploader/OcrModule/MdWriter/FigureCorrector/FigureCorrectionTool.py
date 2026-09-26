"""The tool the writing model calls when a figure box is wrong, correcting it in the same call."""

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..FigureBoard import FigureBoard
from ..Schema import DetectedFigure
from .FigureCorrector import FigureCorrector

logger = logging.getLogger(__name__)

# The name the writing model calls the tool by.
TOOL_NAME = "correct_figures"

# Most corrections one page may ask for, so a model cannot keep redrawing.
DEFAULT_MAX_CALL_COUNT = 2

TOOL_DESCRIPTION = (
    "Have the red figure boxes of your page redrawn, when the layout detector got "
    "them plainly wrong: a box cuts off part of a figure, holds text or another "
    "figure that is not part of it, marks something that is not a figure (a table, "
    "a formula or text), or a figure has no box at all. The boxes are corrected at "
    "once and the page image is sent again with them; then write the page against "
    "the new boxes. Do not call it for a box that is only slightly off."
)

# What the model is told to write in its call.
INSTRUCTION_DESCRIPTION = (
    "What is wrong with which box, and where: for example \"Figure 3 cuts off the "
    "plot's x-axis labels below it\", \"Figure 5 is a table, not a figure\" or "
    "\"the diagram in the lower right has no box\"."
)


@dataclass(frozen=True)
class CorrectionOutcome:
    """What one call of the tool came to.

    Attributes:
        message: The tool's answer to the writing model.
        changed: Whether the page's figures changed, so it is to be shown again.
    """

    message: str
    changed: bool


class FigureCorrectionTool:
    """Offers the writing model the `correct_figures` tool, and runs its calls.

    A call is carried out whole within the call: the FigureCorrector redraws
    the page's boxes, and the board takes them, so the page is written against
    the corrected figures and the document keeps them. A correction that fails
    leaves the figures as they were, and the model is told to carry on."""

    def __init__(
        self,
        corrector: FigureCorrector,
        max_call_count: int = DEFAULT_MAX_CALL_COUNT,
    ) -> None:
        """
        Args:
            corrector: Redraws the boxes of a page.
            max_call_count: Most calls one page may make.
        """
        self.corrector = corrector
        self.max_call_count = max_call_count

    @property
    def definition(self) -> dict[str, Any]:
        """The tool as a chat model's bind_tools takes it."""
        return {
            "type": "function",
            "function": {
                "name": TOOL_NAME,
                "description": TOOL_DESCRIPTION,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "instruction": {
                            "type": "string",
                            "description": INSTRUCTION_DESCRIPTION,
                        }
                    },
                    "required": ["instruction"],
                },
            },
        }

    def session(self, page_index: int, board: FigureBoard) -> "CorrectionSession":
        """The calls of one page's writing, counted against max_call_count."""
        return CorrectionSession(self, page_index, board)


class CorrectionSession:
    """Runs the tool calls the model makes while writing one page."""

    def __init__(
        self, tool: FigureCorrectionTool, page_index: int, board: FigureBoard
    ) -> None:
        """
        Args:
            tool: The tool whose calls are run.
            page_index: The page being written, whose figures a call corrects.
            board: Every page of the document and its figures.
        """
        self._tool = tool
        self._page_index = page_index
        self._board = board
        self._call_count = 0

    @property
    def exhausted(self) -> bool:
        """Whether the page has made every call it may."""
        return self._call_count >= self._tool.max_call_count

    def call(self, name: str, args: Mapping[str, Any]) -> CorrectionOutcome:
        """Runs one tool call, correcting the page's figures if it asks rightly."""
        if name != TOOL_NAME:
            return CorrectionOutcome(f"There is no tool {name!r}.", changed=False)

        instruction = args.get("instruction")
        if not isinstance(instruction, str) or not instruction.strip():
            return CorrectionOutcome(
                "Say in `instruction` what is wrong with which box.", changed=False
            )

        if self.exhausted:
            return CorrectionOutcome(
                "No more corrections can be made for this page: write it with the "
                "boxes as they are.",
                changed=False,
            )
        self._call_count += 1

        before = self._board.figures_on(self._page_index)
        try:
            corrections = self._tool.corrector.correct(
                self._page_index, self._board, instruction
            )
        except Exception:
            # a failed correction leaves the page as it was, never the run broken
            logger.exception("page %d: figure correction failed", self._page_index)
            return CorrectionOutcome(
                "The boxes could not be corrected: write the page with the boxes "
                "as they are.",
                changed=False,
            )

        after = self._board.replace(self._page_index, corrections)
        logger.info(
            "page %d figures corrected: %s -> %s",
            self._page_index,
            _describe(before),
            _describe(after),
        )
        return _outcome(before, after)


def _outcome(
    before: list[DetectedFigure], after: list[DetectedFigure]
) -> CorrectionOutcome:
    """What the model is told of a correction applied to its page."""
    if _boxes(before) == _boxes(after):
        return CorrectionOutcome(
            "The boxes were found right and are unchanged: write the page with them.",
            changed=False,
        )

    before_ids = {figure.block_id for figure in before}
    after_ids = [figure.block_id for figure in after]
    removed = sorted(before_ids - set(after_ids))
    new = [block_id for block_id in after_ids if block_id not in before_ids]

    lines = [
        "The boxes are corrected. Your page's figures are now: "
        + (", ".join(str(block_id) for block_id in after_ids) or "none")
        + "."
    ]
    if new:
        lines.append(f"New: {', '.join(str(block_id) for block_id in new)}.")
    if removed:
        lines.append(
            f"Removed: {', '.join(str(block_id) for block_id in removed)}; "
            "transcribe what they held as text, tables or math."
        )
    lines.append("The page image with the corrected boxes follows.")
    return CorrectionOutcome(" ".join(lines), changed=True)


def _boxes(figures: list[DetectedFigure]) -> list[tuple[int, tuple[int, int, int, int]]]:
    """The figures as comparable (id, box) pairs."""
    return [(figure.block_id, figure.bounding_box) for figure in figures]


def _describe(figures: list[DetectedFigure]) -> str:
    """The figures as `id (x, y, width, height)` for the log."""
    return ", ".join(f"{f.block_id} {f.bounding_box}" for f in figures) or "none"
