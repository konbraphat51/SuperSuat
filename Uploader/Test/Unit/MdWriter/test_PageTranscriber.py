"""Tests for a page being written out as Markdown."""

import base64
from io import BytesIO

import pytest
from FakeModel import RecordingFakeModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from PIL import Image

from OcrModule.MdWriter.FigureBoard import FigureBoard
from OcrModule.MdWriter.FigureCorrector.FigureCorrectionTool import (
    TOOL_NAME,
    FigureCorrectionTool,
)
from OcrModule.MdWriter.FigureCorrector.FigureCorrector import FigureCorrector
from OcrModule.MdWriter.Schema import DetectedFigure, PageTask
from OcrModule.MdWriter.Transcriber.PageTranscriber import Escalation, PageTranscriber

# black all over, so no page is taken as blank
PAGES = [Image.new("RGB", (20, 20), "black") for _ in range(5)]
BLANK = [Image.new("RGB", (20, 20), "white")]
FIGURES = [DetectedFigure(block_id=0, page_index=2, bounding_box=(0, 0, 5, 5))]
TASK = PageTask(page_index=2, page_count=5)

GOOD = "a\n\n![c](figure:0)\n\nb"
REST = "the rest of the text"


def texts(message: HumanMessage) -> list[str]:
    assert isinstance(message.content, list)
    return [
        block["text"]
        for block in message.content
        if isinstance(block, dict) and block.get("type") == "text"
    ]


def images(message: HumanMessage) -> int:
    assert isinstance(message.content, list)
    return sum(
        1
        for block in message.content
        if isinstance(block, dict) and block.get("type") == "image"
    )


def test_a_page_is_sent_alone_labeled_with_its_place_and_figures():
    model = RecordingFakeModel.replying(GOOD)

    markdown = PageTranscriber(model).transcribe(TASK, FigureBoard(PAGES, FIGURES))

    assert markdown == GOOD
    request = model.requests[0][1]
    assert isinstance(request, HumanMessage)
    assert images(request) == 1
    assert texts(request) == ["Page 3 of 5 (figures 0):"]


def test_a_wrapping_code_fence_and_page_markers_are_taken_off():
    model = RecordingFakeModel.replying(f"```markdown\n<!--page:2-->{GOOD}\n```")

    assert PageTranscriber(model).transcribe(TASK, FigureBoard(PAGES, FIGURES)) == GOOD


def test_continuation_markers_are_kept_for_the_stitcher():
    reply = f"<!--continues-previous-->{GOOD}<!--continued-by-next-->"
    model = RecordingFakeModel.replying(reply)

    assert PageTranscriber(model).transcribe(TASK, FigureBoard(PAGES, FIGURES)) == reply


def test_a_failing_answer_is_sent_back_with_its_problems():
    model = RecordingFakeModel.replying("a", GOOD)

    markdown = PageTranscriber(model).transcribe(TASK, FigureBoard(PAGES, FIGURES))

    assert markdown == GOOD
    retry = model.requests[1]
    assert retry[-2].content == "a"
    assert "Figure 0 is not placed" in str(retry[-1].content)


def test_a_page_that_never_checks_out_stops_the_run():
    model = RecordingFakeModel.replying("bad", "bad", "bad")

    with pytest.raises(RuntimeError):
        PageTranscriber(model, max_attempt_count=3).transcribe(
            TASK, FigureBoard(PAGES, FIGURES)
        )

    assert len(model.requests) == 3


def test_a_page_is_sent_no_larger_than_the_set_size():
    model = RecordingFakeModel.replying("a")
    big = [Image.new("RGB", (400, 200), "black")]

    PageTranscriber(model, image_max_edge=100).transcribe(
        PageTask(0, 1), FigureBoard(big, [])
    )

    request = model.requests[0][1]
    assert isinstance(request.content, list)
    image = next(b for b in request.content if b.get("type") == "image")
    decoded = Image.open(BytesIO(base64.b64decode(image["base64"])))
    assert decoded.size == (100, 50)


def test_a_reference_is_sent_after_the_image_with_its_own_prompt():
    model = RecordingFakeModel.replying(GOOD)

    PageTranscriber(model).transcribe(
        TASK, FigureBoard(PAGES, FIGURES), reference="a b c"
    )

    system, request = model.requests[0]
    assert "<reference_ocr>" in str(system.content)
    assert texts(request)[-1] == "<reference_ocr>\na b c\n</reference_ocr>"


def test_a_page_agreeing_with_its_reference_is_not_escalated():
    model = RecordingFakeModel.replying("the rest of the text")
    stronger = RecordingFakeModel.replying()

    markdown = PageTranscriber(
        model, escalation=Escalation(stronger, min_reference_letters=0)
    ).transcribe(PageTask(0, 1), FigureBoard(PAGES, []), reference=REST)

    assert markdown == "the rest of the text"
    assert stronger.requests == []


def test_a_misread_page_is_written_again_by_the_stronger_model():
    model = RecordingFakeModel.replying("something else entirely")
    stronger = RecordingFakeModel.replying("the rest of the text")

    markdown = PageTranscriber(
        model, escalation=Escalation(stronger, min_reference_letters=0)
    ).transcribe(PageTask(0, 1), FigureBoard(PAGES, []), reference=REST)

    assert markdown == "the rest of the text"
    assert len(stronger.requests) == 1


def test_the_first_answer_is_kept_when_the_stronger_one_agrees_less():
    model = RecordingFakeModel.replying("the rest")
    stronger = RecordingFakeModel.replying("unrelated")

    markdown = PageTranscriber(
        model, escalation=Escalation(stronger, min_reference_letters=0)
    ).transcribe(PageTask(0, 1), FigureBoard(PAGES, []), reference=REST)

    assert markdown == "the rest"


def test_a_page_with_too_short_a_reference_is_not_escalated():
    model = RecordingFakeModel.replying("something else entirely")
    stronger = RecordingFakeModel.replying()
    escalation = Escalation(stronger, min_reference_letters=100)

    PageTranscriber(model, escalation=escalation).transcribe(
        PageTask(0, 1), FigureBoard(PAGES, []), reference="Fig. 1 a cat"
    )

    assert stronger.requests == []


def test_a_blank_page_is_written_empty_without_asking_the_model():
    model = RecordingFakeModel.replying()

    markdown = PageTranscriber(model).transcribe(PageTask(0, 1), FigureBoard(BLANK, []))

    assert markdown == ""
    assert model.requests == []


def test_a_blank_page_with_a_figure_is_still_sent_to_the_model():
    model = RecordingFakeModel.replying("![](figure:0)")
    figure = DetectedFigure(block_id=0, page_index=0, bounding_box=(0, 0, 5, 5))

    PageTranscriber(model).transcribe(PageTask(0, 1), FigureBoard(BLANK, [figure]))

    assert len(model.requests) == 1


def test_a_page_the_model_finds_blank_is_written_empty():
    model = RecordingFakeModel.replying("<!--blank-page-->")

    markdown = PageTranscriber(model).transcribe(PageTask(0, 1), FigureBoard(PAGES, []))

    assert markdown == ""


def test_a_blank_page_marker_beside_text_is_sent_back():
    model = RecordingFakeModel.replying("<!--blank-page-->\n\nThis page is blank.", "")

    PageTranscriber(model).transcribe(PageTask(0, 1), FigureBoard(PAGES, []))

    assert "<!--blank-page--> means" in str(model.requests[1][-1].content)


def correction_call(instruction: str = "Figure 0 misses its lower half.") -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {"name": TOOL_NAME, "args": {"instruction": instruction}, "id": "call_1"}
        ],
    )


def correcting(*replies: str, max_call_count: int = 2) -> FigureCorrectionTool:
    corrector = FigureCorrector(RecordingFakeModel.replying(*replies))
    return FigureCorrectionTool(corrector, max_call_count=max_call_count)


def test_without_a_correction_tool_the_model_is_offered_no_tool():
    model = RecordingFakeModel.replying(GOOD)

    PageTranscriber(model).transcribe(TASK, FigureBoard(PAGES, FIGURES))

    assert model.tools == []
    assert "correct_figures" not in str(model.requests[0][0].content)


def test_a_corrected_page_is_shown_again_and_checked_against_its_new_figures():
    board = FigureBoard(PAGES, FIGURES)
    fixed = '{"figures": [{"id": 0, "bbox_2d": [0, 0, 500, 1000]},'
    fixed += ' {"id": null, "bbox_2d": [600, 0, 1000, 500]}]}'
    model = RecordingFakeModel.replying(
        correction_call(), "a\n\n![c](figure:0)\n\n![d](figure:1)"
    )

    markdown = PageTranscriber(model, figure_correction=correcting(fixed)).transcribe(
        TASK, board
    )

    assert markdown == "a\n\n![c](figure:0)\n\n![d](figure:1)"
    assert model.tools[0]["function"]["name"] == TOOL_NAME
    assert "correct_figures" in str(model.requests[0][0].content)
    tool_result, shown_again = model.requests[1][-2:]
    assert isinstance(tool_result, ToolMessage)
    assert "now: 0, 1." in str(tool_result.content)
    assert isinstance(shown_again, HumanMessage)
    assert texts(shown_again) == ["Page 3 of 5 (figures 0, 1):"]
    assert images(shown_again) == 1
    assert board.figures_on(2)[0].bounding_box == (0, 0, 10, 20)


def test_an_unchanged_page_is_not_shown_again():
    unchanged = '{"figures": [{"id": 0, "bbox_2d": [0, 0, 250, 250]}]}'
    model = RecordingFakeModel.replying(correction_call(), GOOD)

    PageTranscriber(model, figure_correction=correcting(unchanged)).transcribe(
        TASK, FigureBoard(PAGES, FIGURES)
    )

    assert isinstance(model.requests[1][-1], ToolMessage)


def test_a_page_calling_past_its_limit_spends_its_attempts():
    model = RecordingFakeModel.replying(*[correction_call()] * 4)

    with pytest.raises(RuntimeError):
        PageTranscriber(
            model,
            max_attempt_count=3,
            figure_correction=correcting('{"figures": []}', max_call_count=1),
        ).transcribe(TASK, FigureBoard(PAGES, FIGURES))

    assert len(model.requests) == 4
    assert "No more corrections" in str(model.requests[-1][-1].content)
