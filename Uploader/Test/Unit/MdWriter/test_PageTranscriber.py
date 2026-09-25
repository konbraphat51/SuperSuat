"""Tests for a page being written out as Markdown."""

import pytest
from FakeModel import RecordingFakeModel
from langchain_core.messages import HumanMessage
from PIL import Image

from OcrModule.MdWriter.Schema import DetectedFigure, PageTask
from OcrModule.MdWriter.Transcriber.PageTranscriber import PageTranscriber

PAGES = [Image.new("RGB", (20, 20), "white") for _ in range(5)]
FIGURES = [DetectedFigure(block_id=0, page_index=2, bounding_box=(0, 0, 5, 5))]
WRITE = PageTask(page_index=2)

GOOD_WRITE = "a\n\n![c](figure:0)\n\nb"


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


def test_a_write_page_sends_its_image_labeled_with_its_figures():
    model = RecordingFakeModel.replying(GOOD_WRITE)

    markdown = PageTranscriber(model).write(WRITE, PAGES, FIGURES)

    assert markdown == GOOD_WRITE
    request = model.requests[0][1]
    assert isinstance(request, HumanMessage)
    assert images(request) == 1
    assert texts(request) == ["Page 2 (figures 0):"]


def test_a_wrapping_code_fence_and_page_markers_are_taken_off():
    model = RecordingFakeModel.replying(f"```markdown\n<!--page:2-->{GOOD_WRITE}\n```")

    assert PageTranscriber(model).write(WRITE, PAGES, FIGURES) == GOOD_WRITE


def test_a_failing_answer_is_sent_back_with_its_problems():
    model = RecordingFakeModel.replying("a", GOOD_WRITE)

    markdown = PageTranscriber(model).write(WRITE, PAGES, FIGURES)

    assert markdown == GOOD_WRITE
    retry = model.requests[1]
    assert retry[-2].content == "a"
    assert "Figure 0 is not placed" in str(retry[-1].content)


def test_a_page_that_never_checks_out_stops_the_run():
    model = RecordingFakeModel.replying("bad", "bad", "bad")

    with pytest.raises(RuntimeError):
        PageTranscriber(model, max_attempt_count=3).write(WRITE, PAGES, FIGURES)

    assert len(model.requests) == 3


FILL = PageTask(page_index=3)


def test_a_fill_page_is_given_both_neighbours_and_only_its_own_image():
    reply = "<!--continues-previous-->rest<!--continued-by-next-->"
    model = RecordingFakeModel.replying(reply)

    markdown = PageTranscriber(model).fill(FILL, PAGES, FIGURES, "before", "after")

    assert markdown == reply
    request = model.requests[0][1]
    assert isinstance(request, HumanMessage)
    assert images(request) == 1
    assert texts(request) == [
        "<previous_page>\nbefore\n</previous_page>",
        "Page 3 (no figures), to transcribe:",
        "<next_page>\nafter\n</next_page>",
    ]


def test_the_last_fill_page_may_not_continue_into_a_next_page():
    last = PageTask(page_index=3)
    model = RecordingFakeModel.replying("a<!--continued-by-next-->", "a")

    markdown = PageTranscriber(model).fill(last, PAGES, FIGURES, "before", None)

    assert markdown == "a"
    assert all("<next_page>" not in t for t in texts(model.requests[0][1]))
