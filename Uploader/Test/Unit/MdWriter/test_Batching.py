"""Tests for the pages being split into write and fill batches."""

import pytest

from OcrModule.MdWriter.Batching import plan_batches


def spans(
    page_count: int, batch_size: int
) -> list[tuple[str, int, int, tuple[int, ...]]]:
    return [
        (batch.kind, batch.first_page, batch.last_page, batch.written_pages)
        for batch in plan_batches(page_count, batch_size)
    ]


def test_a_single_page_is_one_write_batch():
    assert spans(1, 3) == [("write", 0, 0, (0,))]


def test_a_document_shorter_than_a_batch_is_one_write_batch():
    assert spans(3, 5) == [("write", 0, 2, (0, 1, 2))]


def test_batches_share_their_boundary_page_and_fills_write_the_inner_pages():
    assert spans(7, 2) == [
        ("write", 0, 2, (0, 1, 2)),
        ("fill", 2, 4, (3,)),
        ("write", 4, 6, (4, 5, 6)),
    ]


def test_a_document_can_end_on_a_fill_batch():
    assert spans(6, 2) == [
        ("write", 0, 2, (0, 1, 2)),
        ("fill", 2, 4, (3,)),
        ("write", 4, 5, (4, 5)),
    ]
    assert spans(4, 2) == [
        ("write", 0, 2, (0, 1, 2)),
        ("fill", 2, 3, (3,)),
    ]


def test_a_fill_batch_with_nothing_left_to_write_is_dropped():
    # page 3 is both the end of write batch 0 and the start of fill batch 1
    assert spans(4, 3) == [("write", 0, 3, (0, 1, 2, 3))]


def test_every_page_is_written_exactly_once():
    for page_count in range(1, 30):
        for batch_size in range(2, 7):
            written = [
                page
                for batch in plan_batches(page_count, batch_size)
                for page in batch.written_pages
            ]
            assert written == list(range(page_count))


def test_a_batch_size_below_two_is_refused():
    with pytest.raises(ValueError):
        plan_batches(5, 1)
