"""Tests for the headings the text left open being decided from their pages."""

import pytest
from LevelerFakes import image_count, pages, request_text, scripted

import Leveler.PageLeveler as module
from Leveler.Headings import Heading
from Leveler.PageLeveler import PageLeveler
from Leveler.SkeletonLeveler import Skeleton


def headings() -> list[Heading]:
    return [
        Heading(block_index=2, page_index=0, text="Title"),
        Heading(block_index=5, page_index=1, text="1 Sets"),
        Heading(block_index=8, page_index=2, text="Remarks"),
        Heading(block_index=11, page_index=3, text="Notes"),
    ]


def test_every_heading_settled_needs_no_request():
    model = scripted()
    skeleton = Skeleton(levels={2: 1, 5: 2, 8: 3, 11: 3}, uncertain=set())

    levels = PageLeveler(model).level(pages(4), headings(), skeleton)

    assert model.requests == []
    assert levels == {2: 1, 5: 2, 8: 3, 11: 3}


def test_the_open_headings_pages_are_sent_with_one_example_per_level():
    model = scripted({8: 2.5})
    skeleton = Skeleton(levels={2: 1, 5: 2, 8: 3, 11: 3}, uncertain={8})

    levels = PageLeveler(model).level(pages(4), headings(), skeleton)

    # pages 1, 2 and 4 as examples of levels 1, 2 and 3; page 3 to decide
    sent = request_text(model.requests[0])
    assert image_count(model.requests[0]) == 4
    assert "Page 4, showing block 11 as a level 3 heading:" in sent
    assert "Page 3, holding heading block 8 to decide:" in sent
    assert levels == {2: 1, 5: 2, 8: 2.5, 11: 3}


def test_the_outline_marks_the_headings_to_decide_with_their_draft_level():
    model = scripted({8: 3})
    skeleton = Skeleton(levels={2: 1, 5: 2, 8: 3, 11: 3}, uncertain={8})

    PageLeveler(model).level(pages(4), headings(), skeleton)

    sent = request_text(model.requests[0])
    assert '"block_id":5,"page_number":2,"text":"1 Sets","heading_level":2' in sent
    assert '"text":"Remarks","decide":true,"draft_level":3' in sent
    assert "block 5 as a level 2 heading" in sent


def test_the_open_headings_are_split_into_parts_and_later_parts_see_the_earlier(
    monkeypatch,
):
    monkeypatch.setattr(module, "MAX_PAGES_PER_REQUEST", 1)
    model = scripted({8: 2.5}, {11: 2.5})
    skeleton = Skeleton(levels={2: 1, 5: 2, 8: 3, 11: 3}, uncertain={8, 11})

    levels = PageLeveler(model).level(pages(4), headings(), skeleton)

    assert len(model.requests) == 2
    assert '"text":"Remarks","heading_level":2.5' in request_text(model.requests[1])
    assert levels[11] == 2.5


def test_an_open_heading_never_decided_stops_the_run():
    model = scripted({}, {}, {})
    skeleton = Skeleton(levels={2: 1, 5: 2, 8: 3, 11: 3}, uncertain={8})

    with pytest.raises(RuntimeError, match="1 heading"):
        PageLeveler(model).level(pages(4), headings(), skeleton)


def test_a_page_sent_to_decide_is_not_sent_again_as_an_example():
    model = scripted({11: 3})
    same_page = [*headings()[:3], Heading(block_index=11, page_index=2, text="Notes")]
    skeleton = Skeleton(levels={2: 1, 5: 2, 8: 3, 11: 3}, uncertain={11})

    PageLeveler(model).level(pages(4), same_page, skeleton)

    assert image_count(model.requests[0]) == 3
    assert "Page 3, showing" not in request_text(model.requests[0])
