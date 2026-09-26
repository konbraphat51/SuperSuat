"""Tests for the entries of a table of contents block being read and checked."""

from OcrModule.MdWriter.TableOfContents import entry_problems, parse_entries
from OcrModule.OcrSchema import TableOfContentsEntry


def entry(
    number: str | None,
    title: str,
    page: str | None,
    children: list[TableOfContentsEntry] | None = None,
) -> TableOfContentsEntry:
    return TableOfContentsEntry(number, title, page, children or [])


def test_entries_are_nested_by_their_indentation():
    text = (
        "- | Preface | iv\n"
        "- 1 | Introduction | 1\n"
        "  - 1.1 | Background | 3\n"
        "    - 1.1.1 | History | 4\n"
        "  - 1.2 | Aims | 7\n"
        "- 2 | Method | 11\n"
    )

    assert parse_entries(text) == [
        entry(None, "Preface", "iv"),
        entry(
            "1",
            "Introduction",
            "1",
            [
                entry("1.1", "Background", "3", [entry("1.1.1", "History", "4")]),
                entry("1.2", "Aims", "7"),
            ],
        ),
        entry("2", "Method", "11"),
    ]


def test_any_consistent_indentation_nests_and_blank_lines_are_skipped():
    text = "* 第1章 | 総論 | 1\n\n\t+ 第1節 | 目的 | 2\n* 第2章 | 各論 |"

    assert parse_entries(text) == [
        entry("第1章", "総論", "1", [entry("第1節", "目的", "2")]),
        entry("第2章", "各論", None),
    ]


def test_a_pipe_in_a_title_is_kept_escaped_or_not():
    assert parse_entries("- 1 | A \\| B | 2\n- 2 | C | D | 3") == [
        entry("1", "A | B", "2"),
        entry("2", "C|D", "3"),
    ]


def test_an_entry_indented_under_nothing_is_outermost():
    assert parse_entries("  - 1.3 | Rest | 9\n- 2 | Next | 12") == [
        entry("1.3", "Rest", "9"),
        entry("2", "Next", "12"),
    ]


def test_lines_that_are_not_entries_are_reported():
    body = (
        "text | not | in a block\n\n"
        ":::toc\n- 1 | Fine | 1\nIntroduction ...... 1\n- 2 | Method\n- 3 |  | 5\n:::"
    )

    problems = entry_problems(body)

    assert len(problems) == 3
    assert '"Introduction ...... 1"' in problems[0]
    assert '"- 2 | Method"' in problems[1]
    assert '"- 3 |  | 5"' in problems[2]
