"""Tests for the heading hierarchy being laid out from text and tables of contents."""

import pytest
from LevelerFakes import image_count, request_text, scripted

from Leveler.Headings import Heading
from Leveler.SkeletonLeveler import SkeletonLeveler
from OcrModule.OcrSchema import OcrResultBlockTableOfContents, TableOfContentsEntry


def headings() -> list[Heading]:
    return [
        Heading(block_index=2, page_index=0, text="1 Sets"),
        Heading(block_index=5, page_index=1, text="1.1 Operations"),
        Heading(block_index=8, page_index=1, text="Remarks"),
    ]


def contents() -> OcrResultBlockTableOfContents:
    return OcrResultBlockTableOfContents(
        block_type="table_of_contents",
        existing_pages=[0],
        block_index=1,
        entries=[
            TableOfContentsEntry(
                section_number="1",
                title="Sets",
                page_number="1",
                children=[TableOfContentsEntry("1.1", "Operations", "3")],
            )
        ],
    )


def test_every_heading_is_leveled_and_the_open_ones_are_marked():
    model = scripted({2: 2, 5: 3, 8: (4, True)})

    skeleton = SkeletonLeveler(model).level(headings(), [contents()])

    assert skeleton.levels == {2: 2, 5: 3, 8: 4}
    assert skeleton.uncertain == {8}


def test_the_tables_of_contents_and_headings_are_sent_as_text_only():
    model = scripted({2: 2, 5: 3, 8: 4})

    SkeletonLeveler(model).level(headings(), [contents()])

    sent = request_text(model.requests[0])
    assert "- 1 | Sets | 1\n  - 1.1 | Operations | 3" in sent
    assert '"block_id":8,"page_number":2,"text":"Remarks"' in sent
    assert image_count(model.requests[0]) == 0
    assert model.answer_types == ["SkeletonLevels"]


def test_a_document_without_a_table_of_contents_says_so():
    model = scripted({2: 2, 5: 3, 8: 4})

    SkeletonLeveler(model).level(headings(), [])

    assert "The document has no table of contents." in request_text(model.requests[0])


def test_a_heading_left_out_or_above_the_title_is_asked_about_again():
    model = scripted({2: 0, 5: 3}, {2: 2, 8: (4, True)})

    skeleton = SkeletonLeveler(model).level(headings(), [])

    retry = str(model.requests[1][-1].content)
    assert "nothing sits above it" in retry
    assert "These headings still have no level: 2, 8." in retry
    assert skeleton.levels == {2: 2, 5: 3, 8: 4}
    assert skeleton.uncertain == {8}


def test_a_heading_never_leveled_stops_the_run():
    model = scripted({2: 2}, {2: 2}, {2: 2})

    with pytest.raises(RuntimeError, match="2 heading"):
        SkeletonLeveler(model).level(headings(), [])
