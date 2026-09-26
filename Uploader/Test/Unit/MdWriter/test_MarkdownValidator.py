"""Tests for a page's Markdown being checked before it is used."""

from OcrModule.MdWriter.Transcriber.MarkdownValidator import validate_page_output


def test_a_complete_page_passes():
    markdown = "a\n\n![c](figure:0)\n\nb"

    assert validate_page_output(markdown, [0]) == []


def test_a_figure_whose_caption_holds_an_interval_passes():
    markdown = "a\n\n![The interval \\([a, b]\\)](figure:0)\n\nb"

    assert validate_page_output(markdown, [0]) == []


def test_a_page_may_continue_both_ways():
    markdown = "<!--continues-previous-->rest of it<!--continued-by-next-->"

    assert validate_page_output(markdown, []) == []


def test_figures_unknown_repeated_and_missing_are_reported():
    markdown = "![a](figure:0)\n\n![b](figure:0)\n\n![c](figure:9)"

    problems = validate_page_output(markdown, [0, 1])

    assert len(problems) == 3
    assert "no figure 9" in problems[0]
    assert "figure 0 only once" in problems[1]
    assert "Figure 1 is not placed" in problems[2]


def test_a_continuation_marker_in_the_middle_is_reported():
    problems = validate_page_output("a<!--continues-previous-->b", [])

    assert any("very first thing" in p for p in problems)


def test_an_unclosed_box_is_reported():
    problems = validate_page_output(":::column\na", [])

    assert any("never closed" in p for p in problems)


def test_a_page_written_twice_is_reported():
    paragraph = "A paragraph long enough that repeating it is no accident at all."
    markdown = f"{paragraph}\n\n{paragraph}"

    problems = validate_page_output(markdown, [])

    assert len(problems) == 1
    assert "written 2 times" in problems[0]


def test_a_short_line_the_document_repeats_is_not_reported():
    markdown = "Answer:\n\nAnswer:"

    assert validate_page_output(markdown, []) == []


def test_a_figure_sharing_its_paragraph_is_reported():
    for markdown in (
        "![c](figure:0)text",
        "text\n![c](figure:0)",
        "![c](figure:0)\ntext",
    ):
        problems = validate_page_output(markdown, [0])

        assert any("shares its paragraph" in p for p in problems), markdown


def test_a_figure_right_inside_a_box_is_its_own_paragraph():
    markdown = ":::column\n![c](figure:0)\n:::"

    assert validate_page_output(markdown, [0]) == []


def test_a_table_of_contents_passes_and_a_line_that_is_no_entry_is_reported():
    markdown = "## Contents\n\n:::toc\n- 1 | Introduction | 1\n  - 1.1 | Aims | 2\n:::"

    assert validate_page_output(markdown, []) == []

    problems = validate_page_output(":::toc\nIntroduction ... 1\n:::", [])

    assert len(problems) == 1
    assert "not an entry" in problems[0]


def test_a_blank_page_marker_alone_passes():
    assert validate_page_output("<!--blank-page-->", []) == []


def test_a_blank_page_marker_beside_text_is_reported():
    problems = validate_page_output("<!--blank-page-->\n\nThis page is blank.", [])

    assert len(problems) == 1
    assert "<!--blank-page-->" in problems[0]


def test_a_blank_page_marker_on_a_page_with_figures_leaves_them_missing():
    problems = validate_page_output("<!--blank-page-->", [3])

    assert any("Figure 3 is not placed" in problem for problem in problems)
