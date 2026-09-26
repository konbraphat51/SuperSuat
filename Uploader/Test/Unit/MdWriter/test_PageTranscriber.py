"""Tests for a page being written out as Markdown."""

import base64
from io import BytesIO

import pytest
from FakeModel import RecordingFakeModel
from langchain_core.messages import HumanMessage
from PIL import Image

from OcrModule.MdWriter.Schema import DetectedFigure, PageTask
from OcrModule.MdWriter.Transcriber.PageTranscriber import Escalation, PageTranscriber

PAGES = [Image.new("RGB", (20, 20), "white") for _ in range(5)]
FIGURES = [DetectedFigure(block_id=0, page_index=2, bounding_box=(0, 0, 5, 5))]
TASK = PageTask(page_index=2, page_count=5)

GOOD = "a\n\n![c](figure:0)\n\nb"


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

    markdown = PageTranscriber(model).transcribe(TASK, PAGES, FIGURES)

    assert markdown == GOOD
    request = model.requests[0][1]
    assert isinstance(request, HumanMessage)
    assert images(request) == 1
    assert texts(request) == ["Page 3 of 5 (figures 0):"]


def test_a_wrapping_code_fence_and_page_markers_are_taken_off():
    model = RecordingFakeModel.replying(f"```markdown\n<!--page:2-->{GOOD}\n```")

    assert PageTranscriber(model).transcribe(TASK, PAGES, FIGURES) == GOOD


def test_continuation_markers_are_kept_for_the_stitcher():
    reply = f"<!--continues-previous-->{GOOD}<!--continued-by-next-->"
    model = RecordingFakeModel.replying(reply)

    assert PageTranscriber(model).transcribe(TASK, PAGES, FIGURES) == reply


def test_a_failing_answer_is_sent_back_with_its_problems():
    model = RecordingFakeModel.replying("a", GOOD)

    markdown = PageTranscriber(model).transcribe(TASK, PAGES, FIGURES)

    assert markdown == GOOD
    retry = model.requests[1]
    assert retry[-2].content == "a"
    assert "Figure 0 is not placed" in str(retry[-1].content)


def test_a_page_that_never_checks_out_stops_the_run():
    model = RecordingFakeModel.replying("bad", "bad", "bad")

    with pytest.raises(RuntimeError):
        PageTranscriber(model, max_attempt_count=3).transcribe(TASK, PAGES, FIGURES)

    assert len(model.requests) == 3


def test_a_page_is_sent_no_larger_than_the_set_size():
    model = RecordingFakeModel.replying("a")
    big = [Image.new("RGB", (400, 200), "white")]

    PageTranscriber(model, image_max_edge=100).transcribe(PageTask(0, 1), big, [])

    request = model.requests[0][1]
    assert isinstance(request.content, list)
    image = next(b for b in request.content if b.get("type") == "image")
    decoded = Image.open(BytesIO(base64.b64decode(image["base64"])))
    assert decoded.size == (100, 50)


def test_a_reference_is_sent_after_the_image_with_its_own_prompt():
    model = RecordingFakeModel.replying(GOOD)

    PageTranscriber(model).transcribe(TASK, PAGES, FIGURES, reference="a b c")

    system, request = model.requests[0]
    assert "<reference_ocr>" in str(system.content)
    assert texts(request)[-1] == "<reference_ocr>\na b c\n</reference_ocr>"


def test_a_page_agreeing_with_its_reference_is_not_escalated():
    model = RecordingFakeModel.replying("文章の続き")
    stronger = RecordingFakeModel.replying()

    markdown = PageTranscriber(model, escalation=Escalation(stronger)).transcribe(
        PageTask(0, 1), PAGES, [], reference="文章の続き"
    )

    assert markdown == "文章の続き"
    assert stronger.requests == []


def test_a_misread_page_is_written_again_by_the_stronger_model():
    model = RecordingFakeModel.replying("まったく違う文")
    stronger = RecordingFakeModel.replying("文章の続き")

    markdown = PageTranscriber(model, escalation=Escalation(stronger)).transcribe(
        PageTask(0, 1), PAGES, [], reference="文章の続き"
    )

    assert markdown == "文章の続き"
    assert len(stronger.requests) == 1


def test_the_first_answer_is_kept_when_the_stronger_one_agrees_less():
    model = RecordingFakeModel.replying("文章の")
    stronger = RecordingFakeModel.replying("無関係")

    markdown = PageTranscriber(model, escalation=Escalation(stronger)).transcribe(
        PageTask(0, 1), PAGES, [], reference="文章の続き"
    )

    assert markdown == "文章の"
