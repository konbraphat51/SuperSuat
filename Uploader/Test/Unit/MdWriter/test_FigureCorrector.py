"""Tests for a page's figure boxes being redrawn by a grounding model."""

import json

import pytest
from FakeModel import RecordingFakeModel
from PIL import Image

from OcrModule.MdWriter.FigureBoard import FigureBoard
from OcrModule.MdWriter.FigureCorrector.FigureCorrector import (
    FigureCorrector,
    parse_corrections,
    to_normalized,
)
from OcrModule.MdWriter.Schema import CorrectedFigure, DetectedFigure

SIZE = (200, 100)
PAGES = [Image.new("RGB", SIZE, "white")]
FIGURES = [DetectedFigure(block_id=4, page_index=0, bounding_box=(20, 10, 40, 30))]


def answer(*figures: tuple[int | None, list[float]]) -> str:
    return json.dumps(
        {"figures": [{"id": fid, "bbox_2d": box} for fid, box in figures]}
    )


def test_boxes_are_scaled_from_0_to_1000_onto_the_page():
    corrections, problems = parse_corrections(
        answer((4, [100, 100, 500, 500]), (None, [500, 0, 1000, 1000])), [4], SIZE
    )

    assert problems == []
    assert corrections == [
        CorrectedFigure(4, (20, 10, 80, 40)),
        CorrectedFigure(None, (100, 0, 100, 100)),
    ]


def test_a_box_is_scaled_to_0_to_1000_and_back_unchanged():
    normalized = to_normalized((20, 10, 40, 30), SIZE)

    corrections, _ = parse_corrections(answer((4, normalized)), [4], SIZE)

    assert normalized == [100, 100, 300, 400]
    assert corrections[0].bounding_box == (20, 10, 40, 30)


def test_a_fenced_answer_and_a_corner_off_the_page_are_taken_as_they_mean():
    fenced = f"```json\n{answer((None, [-5, 0, 1004, 500]))}\n```"

    corrections, problems = parse_corrections(fenced, [], SIZE)

    assert problems == []
    assert corrections == [CorrectedFigure(None, (0, 0, 200, 50))]


def test_an_empty_list_removes_every_figure():
    assert parse_corrections('{"figures": []}', [4], SIZE) == ([], [])


def test_an_answer_that_is_no_json_is_reported():
    _, problems = parse_corrections("The box is fine.", [4], SIZE)

    assert problems == ['Answer with the JSON object {"figures": [...]} and nothing else.']


def test_unknown_repeated_ids_and_broken_boxes_are_reported():
    _, problems = parse_corrections(
        answer(
            (9, [0, 0, 10, 10]),
            (4, [0, 0, 10, 10]),
            (4, [0, 0, 20, 20]),
            (None, [50, 50, 10, 10]),
        ),
        [4],
        SIZE,
    )

    assert len(problems) == 3
    assert "id 9" in problems[0]
    assert "repeats id 4" in problems[1]
    assert "x1 < x2" in problems[2]


def test_the_model_is_shown_the_page_twice_with_the_boxes_and_the_request():
    model = RecordingFakeModel.replying(answer((4, [0, 0, 500, 500])))

    corrections = FigureCorrector(model).correct(
        0, FigureBoard(PAGES, FIGURES), "Figure 4 cuts off the legend."
    )

    assert corrections == [CorrectedFigure(4, (0, 0, 100, 50))]
    request = model.requests[0][1].content
    assert isinstance(request, list)
    assert sum(1 for block in request if block.get("type") == "image") == 2
    assert '[{"id": 4, "bbox_2d": [100, 100, 300, 400]}]' in request[-1]["text"]
    assert "Figure 4 cuts off the legend." in request[-1]["text"]


def test_a_failing_answer_is_sent_back_and_a_lasting_one_stops_the_correction():
    model = RecordingFakeModel.replying("no", "no")

    with pytest.raises(RuntimeError):
        FigureCorrector(model, max_attempt_count=2).correct(
            0, FigureBoard(PAGES, FIGURES), "Figure 4 is too small."
        )

    assert "cannot be used" in str(model.requests[1][-1].content)
