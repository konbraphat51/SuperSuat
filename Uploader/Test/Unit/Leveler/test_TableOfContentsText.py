"""Tests for the tables of contents being written out as text for the leveler model."""

from Leveler.TableOfContentsText import (
    collect_tables_of_contents,
    table_of_contents_text,
)
from OcrModule.OcrSchema import (
    OcrResultBlockTableOfContents,
    OcrResultBlockText,
    TableOfContentsEntry,
)


def entry(
    number: str | None,
    title: str,
    page: str | None,
    *children: TableOfContentsEntry,
) -> TableOfContentsEntry:
    return TableOfContentsEntry(
        section_number=number, title=title, page_number=page, children=list(children)
    )


def table(
    block_index: int, pages: list[int], *entries: TableOfContentsEntry
) -> OcrResultBlockTableOfContents:
    return OcrResultBlockTableOfContents(
        block_type="table_of_contents",
        existing_pages=pages,
        block_index=block_index,
        entries=list(entries),
    )


def test_entries_are_indented_by_how_deep_they_are_nested():
    contents = table(
        5,
        [2, 3],
        entry("1", "Sets", "1", entry("1.1", "Operations", "3")),
        entry("2", "Models", "9"),
    )

    assert table_of_contents_text([contents]) == (
        "Table of contents block 5, printed on pages 3-4:\n"
        "- 1 | Sets | 1\n"
        "  - 1.1 | Operations | 3\n"
        "- 2 | Models | 9"
    )


def test_a_missing_number_or_page_is_left_empty():
    contents = table(7, [0], entry(None, "Preface", None))

    assert table_of_contents_text([contents]) == (
        "Table of contents block 7, printed on page 1:\n- | Preface |"
    )


def test_several_tables_are_kept_apart_and_none_is_empty():
    first = table(1, [0], entry("1", "A", "1"))
    second = table(2, [9], entry("1.1", "B", "2"))

    assert "\n\nTable of contents block 2" in table_of_contents_text([first, second])
    assert table_of_contents_text([]) == ""


def test_only_the_table_of_contents_blocks_are_collected():
    paragraph = OcrResultBlockText(
        block_type="paragraph", existing_pages=[0], block_index=1, text="text"
    )
    contents = table(2, [0], entry("1", "A", "1"))

    assert collect_tables_of_contents([paragraph, contents]) == [contents]
