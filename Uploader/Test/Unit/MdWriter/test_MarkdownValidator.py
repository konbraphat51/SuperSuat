"""Tests for a page's Markdown being checked before it is used."""

from OcrModule.MdWriter.MarkdownValidator import validate_page_output
from OcrModule.MdWriter.Schema import PageTask

WRITE = PageTask(page_index=0)
FILL = PageTask(page_index=1)


def test_a_complete_write_page_passes():
    markdown = "a\n\n![c](figure:0)\n\nb"

    assert validate_page_output(markdown, WRITE, [0], has_next=True) == []


def test_a_fill_page_may_continue_both_ways():
    markdown = "<!--continues-previous-->rest of it<!--continued-by-next-->"

    assert validate_page_output(markdown, FILL, [], has_next=True) == []


def test_figures_unknown_repeated_and_missing_are_reported():
    markdown = "![a](figure:0)\n\n![b](figure:0)\n\n![c](figure:9)"

    problems = validate_page_output(markdown, WRITE, [0, 1], has_next=False)

    assert len(problems) == 3
    assert "no figure 9" in problems[0]
    assert "figure 0 only once" in problems[1]
    assert "Figure 1 is not placed" in problems[2]


def test_a_write_page_may_not_use_continuation_markers():
    markdown = "<!--continues-previous-->text"

    problems = validate_page_output(markdown, WRITE, [], has_next=True)

    assert any("no neighbouring page" in p for p in problems)


def test_the_last_fill_page_may_not_continue_into_nothing():
    problems = validate_page_output(
        "text<!--continued-by-next-->", FILL, [], has_next=False
    )

    assert any("no page follows yours" in p for p in problems)


def test_a_continuation_marker_in_the_middle_is_reported():
    problems = validate_page_output(
        "a<!--continues-previous-->b", FILL, [], has_next=True
    )

    assert any("very first thing" in p for p in problems)


def test_an_unclosed_box_is_reported():
    problems = validate_page_output(":::column\na", WRITE, [], has_next=False)

    assert any("never closed" in p for p in problems)


def test_a_page_written_twice_is_reported():
    paragraph = "A paragraph long enough that repeating it is no accident at all."
    markdown = f"{paragraph}\n\n{paragraph}"

    problems = validate_page_output(markdown, WRITE, [], has_next=False)

    assert len(problems) == 1
    assert "written 2 times" in problems[0]


def test_a_short_line_the_document_repeats_is_not_reported():
    markdown = "Answer:\n\nAnswer:"

    assert validate_page_output(markdown, WRITE, [], has_next=False) == []
