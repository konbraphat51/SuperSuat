"""Tests for a batch of pages being written out as Markdown."""

import pytest
from FakeModel import RecordingFakeModel
from langchain_core.messages import HumanMessage
from PIL import Image

from OcrModule.LinearMD.Schema import DetectedFigure, PageBatch
from OcrModule.LinearMD.Transcriber.BatchTranscriber import BatchTranscriber

PAGES = [Image.new("RGB", (20, 20), "white") for _ in range(5)]
FIGURES = [DetectedFigure(block_id=0, page_index=1, bounding_box=(0, 0, 5, 5))]
WRITE = PageBatch(index=0, first_page=0, last_page=2, written_pages=(0, 1, 2))

GOOD_WRITE = "<!--page:0-->a\n\n<!--page:1-->![c](figure:0)\n\n<!--page:2-->b"


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


def test_a_write_batch_sends_every_page_labeled_with_its_figures():
    model = RecordingFakeModel.replying(GOOD_WRITE)

    markdown = BatchTranscriber(model).write(WRITE, PAGES, FIGURES)

    assert markdown == GOOD_WRITE
    request = model.requests[0][1]
    assert isinstance(request, HumanMessage)
    assert images(request) == 3
    assert "Page 1 (figures 0):" in texts(request)
    assert "Page 2 (no figures):" in texts(request)


def test_a_wrapping_code_fence_is_taken_off():
    model = RecordingFakeModel.replying(f"```markdown\n{GOOD_WRITE}\n```")

    assert BatchTranscriber(model).write(WRITE, PAGES, FIGURES) == GOOD_WRITE


def test_a_failing_answer_is_sent_back_with_its_problems():
    model = RecordingFakeModel.replying("<!--page:0-->a", GOOD_WRITE)

    markdown = BatchTranscriber(model).write(WRITE, PAGES, FIGURES)

    assert markdown == GOOD_WRITE
    retry = model.requests[1]
    assert retry[-2].content == "<!--page:0-->a"
    assert "Figure 0 is not placed" in str(retry[-1].content)


def test_a_batch_that_never_checks_out_stops_the_run():
    model = RecordingFakeModel.replying("bad", "bad", "bad")

    with pytest.raises(RuntimeError):
        BatchTranscriber(model, max_attempt_count=3).write(WRITE, PAGES, FIGURES)

    assert len(model.requests) == 3


FILL = PageBatch(index=1, first_page=2, last_page=4, written_pages=(3,))


def test_a_fill_batch_is_given_both_neighbours_and_its_boundary_pages():
    reply = "<!--continues-previous--><!--page:3-->rest<!--continued-by-next-->"
    model = RecordingFakeModel.replying(reply)

    markdown = BatchTranscriber(model).fill(
        FILL, PAGES, FIGURES, "<!--page:0-->before", "<!--page:4-->after"
    )

    assert markdown == reply
    request = model.requests[0][1]
    assert isinstance(request, HumanMessage)
    sent = texts(request)
    assert images(request) == 3
    assert sent[0] == "<previous_part>\n<!--page:0-->before\n</previous_part>"
    assert "Page 2 (no figures), already transcribed, context only:" in sent
    assert "Page 3 (no figures), to transcribe:" in sent
    assert "<next_part>\n<!--page:4-->after\n</next_part>" in sent


def test_the_last_fill_batch_may_not_continue_into_a_next_part():
    last = PageBatch(index=1, first_page=2, last_page=3, written_pages=(3,))
    model = RecordingFakeModel.replying(
        "<!--page:3-->a<!--continued-by-next-->", "<!--page:3-->a"
    )

    markdown = BatchTranscriber(model).fill(last, PAGES, FIGURES, "before", None)

    assert markdown == "<!--page:3-->a"
    assert all("<next_part>" not in t for t in texts(model.requests[0][1]))
