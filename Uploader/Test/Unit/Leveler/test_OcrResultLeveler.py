"""Tests for a transcribed document tree being nested by its heading levels."""

from LevelerFakes import image_count, pages, scripted, section, shape, text

from Leveler.OcrResultLeveler import OcrResultLeveler
from OcrModule.OcrSchema import (
    OcrResult,
    OcrResultBlockTableOfContents,
    TableOfContentsEntry,
)


def flat_document() -> OcrResult:
    """A document whose headings all sit one level deep, as MdWriter writes it."""
    return OcrResult(
        root_section=section(
            0,
            section(1, text(2, "heading"), text(3)),
            section(4, text(5, "heading", page=1), text(6, page=1)),
            section(7, text(8, "heading", page=1), text(9, page=1)),
        )
    )


def test_a_flat_document_is_nested_by_the_levels_the_text_settles():
    model = scripted({2: 1, 5: 2, 8: 3})
    document = flat_document()

    leveled = OcrResultLeveler(model).level_ocr_result(pages(2), document)

    assert shape(leveled.root_section) == [[2, 3, [5, 6, [8, 9]]]]
    assert leveled.root_section.block_index == 0
    # the given tree is left as it was
    assert shape(document.root_section) == [[2, 3], [5, 6], [8, 9]]


def test_no_page_is_looked_at_when_the_text_settles_every_heading():
    model = scripted({2: 1, 5: 2, 8: 2})

    OcrResultLeveler(model).level_ocr_result(pages(2), flat_document())

    assert model.answer_types == ["SkeletonLevels"]


def test_an_open_heading_is_decided_from_its_page_and_may_fall_between_levels():
    model = scripted({2: 2, 5: (3, True), 8: 3}, {5: 2.5})

    leveled = OcrResultLeveler(model).level_ocr_result(pages(2), flat_document())

    assert model.answer_types == ["SkeletonLevels", "HeadingLevels"]
    assert image_count(model.requests[1]) >= 1
    assert shape(leveled.root_section) == [[2, 3, [5, 6, [8, 9]]]]


def test_the_tables_of_contents_reach_the_skeleton():
    model = scripted({2: 2})
    contents = OcrResultBlockTableOfContents(
        block_type="table_of_contents",
        existing_pages=[0],
        block_index=1,
        entries=[TableOfContentsEntry("1", "Sets", "1")],
    )
    document = OcrResult(root_section=section(0, contents, text(2, "heading")))

    leveled = OcrResultLeveler(model).level_ocr_result(pages(1), document)

    assert "- 1 | Sets | 1" in str(model.requests[0][-1].content)
    assert shape(leveled.root_section) == [1, [2]]


def test_a_document_without_headings_asks_nothing_and_stays_flat():
    model = scripted()
    document = OcrResult(root_section=section(0, text(1), text(2)))

    leveled = OcrResultLeveler(model).level_ocr_result(pages(1), document)

    assert model.requests == []
    assert shape(leveled.root_section) == [1, 2]
