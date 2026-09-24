"""Tests for a batch's Markdown being checked before it is used."""

from OcrModule.LinearMD.MarkdownValidator import validate_batch_output
from OcrModule.LinearMD.Schema import PageBatch

WRITE = PageBatch(index=0, first_page=0, last_page=2, written_pages=(0, 1, 2))
FILL = PageBatch(index=1, first_page=2, last_page=4, written_pages=(3,))


def test_a_complete_write_batch_passes():
    markdown = "<!--page:0-->a\n\n<!--page:1-->![c](figure:0)\n\n<!--page:2-->b"

    assert validate_batch_output(markdown, WRITE, [0], has_next=True) == []


def test_a_fill_batch_may_continue_both_ways():
    markdown = (
        "<!--continues-previous--><!--page:3-->rest of it<!--continued-by-next-->"
    )

    assert validate_batch_output(markdown, FILL, [], has_next=True) == []


def test_missing_or_misordered_page_markers_are_reported():
    problems = validate_batch_output(
        "<!--page:0-->a<!--page:2-->b<!--page:1-->c", WRITE, [], has_next=False
    )

    assert len(problems) == 1
    assert "<!--page:0-->, <!--page:1-->, <!--page:2-->" in problems[0]


def test_output_must_open_with_its_first_page_marker():
    problems = validate_batch_output(
        "preamble <!--page:3-->text", FILL, [], has_next=True
    )

    assert any("Start your output with <!--page:3-->" in p for p in problems)


def test_figures_unknown_repeated_and_missing_are_reported():
    markdown = (
        "<!--page:0-->![a](figure:0)![b](figure:0)"
        "<!--page:1-->![c](figure:9)<!--page:2-->"
    )

    problems = validate_batch_output(markdown, WRITE, [0, 1], has_next=False)

    assert len(problems) == 3
    assert "no figure 9" in problems[0]
    assert "figure 0 only once" in problems[1]
    assert "Figure 1 is not placed" in problems[2]


def test_a_write_batch_may_not_use_continuation_markers():
    markdown = "<!--continues-previous--><!--page:0--><!--page:1--><!--page:2-->"

    problems = validate_batch_output(markdown, WRITE, [], has_next=True)

    assert any("no neighbouring part" in p for p in problems)


def test_the_last_fill_batch_may_not_continue_into_nothing():
    problems = validate_batch_output(
        "<!--page:3-->text<!--continued-by-next-->", FILL, [], has_next=False
    )

    assert any("no part follows yours" in p for p in problems)


def test_a_continuation_marker_in_the_middle_is_reported():
    problems = validate_batch_output(
        "<!--page:3-->a<!--continues-previous-->b", FILL, [], has_next=True
    )

    assert any("very first thing" in p for p in problems)


def test_an_unclosed_box_is_reported():
    problems = validate_batch_output(
        "<!--page:0-->:::column\na<!--page:1--><!--page:2-->", WRITE, [], has_next=False
    )

    assert any("never closed" in p for p in problems)
