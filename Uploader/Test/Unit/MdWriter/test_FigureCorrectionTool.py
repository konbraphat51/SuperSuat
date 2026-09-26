"""Tests for the writing model's tool calls correcting its page's figures."""

from FakeModel import RecordingFakeModel
from PIL import Image

from OcrModule.MdWriter.FigureBoard import FigureBoard
from OcrModule.MdWriter.FigureCorrector.FigureCorrectionTool import (
    TOOL_NAME,
    FigureCorrectionTool,
)
from OcrModule.MdWriter.FigureCorrector.FigureCorrector import FigureCorrector
from OcrModule.MdWriter.Schema import DetectedFigure

PAGES = [Image.new("RGB", (100, 100), "white") for _ in range(2)]
ASK = {"instruction": "Figure 0 cuts off the legend."}


def board() -> FigureBoard:
    return FigureBoard(
        PAGES,
        [
            DetectedFigure(block_id=0, page_index=0, bounding_box=(10, 10, 20, 20)),
            DetectedFigure(block_id=1, page_index=1, bounding_box=(0, 0, 50, 50)),
        ],
    )


def tool(*replies: str, max_call_count: int = 2) -> FigureCorrectionTool:
    model = RecordingFakeModel.replying(*replies)
    return FigureCorrectionTool(
        FigureCorrector(model, max_attempt_count=1), max_call_count=max_call_count
    )


def test_the_tool_is_offered_by_its_name_with_an_instruction():
    definition = tool().definition

    assert definition["function"]["name"] == TOOL_NAME
    assert definition["function"]["parameters"]["required"] == ["instruction"]


def test_a_call_corrects_the_page_on_the_board_at_once():
    figures = board()
    reply = '{"figures": [{"id": 0, "bbox_2d": [100, 100, 600, 600]},'
    reply += ' {"id": null, "bbox_2d": [700, 700, 900, 900]}]}'

    outcome = tool(reply).session(0, figures).call(TOOL_NAME, ASK)

    assert outcome.changed
    assert "now: 0, 2." in outcome.message
    assert "New: 2." in outcome.message
    assert figures.figures_on(0)[0].bounding_box == (10, 10, 50, 50)
    assert figures.figure_ids_on(1) == [1]


def test_a_removed_figure_is_to_be_transcribed_as_text():
    figures = board()

    outcome = tool('{"figures": []}').session(0, figures).call(TOOL_NAME, ASK)

    assert outcome.changed
    assert "Removed: 0" in outcome.message
    assert figures.figure_ids_on(0) == []


def test_boxes_found_right_leave_the_page_as_it_was():
    reply = '{"figures": [{"id": 0, "bbox_2d": [100, 100, 300, 300]}]}'

    outcome = tool(reply).session(0, board()).call(TOOL_NAME, ASK)

    assert not outcome.changed
    assert "unchanged" in outcome.message


def test_a_failed_correction_leaves_the_figures_and_lets_the_page_go_on():
    figures = board()

    outcome = tool("not json").session(0, figures).call(TOOL_NAME, ASK)

    assert not outcome.changed
    assert "could not be corrected" in outcome.message
    assert figures.figures_on(0)[0].bounding_box == (10, 10, 20, 20)


def test_a_page_makes_no_more_calls_than_it_may():
    session = tool('{"figures": []}', max_call_count=1).session(0, board())

    session.call(TOOL_NAME, ASK)
    outcome = session.call(TOOL_NAME, ASK)

    assert session.exhausted
    assert not outcome.changed
    assert "No more corrections" in outcome.message


def test_a_call_without_an_instruction_or_to_another_tool_does_nothing():
    session = tool().session(0, board())

    assert not session.call(TOOL_NAME, {}).changed
    assert "no tool" in session.call("other", ASK).message
    assert not session.exhausted
