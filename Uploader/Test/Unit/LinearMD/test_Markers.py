"""Tests for the markers the model writes being found and taken out."""

from OcrModule.LinearMD.Markers import (
    PageMark,
    find_figure_references,
    find_page_markers,
    split_continuation,
    split_leading_page_markers,
    strip_page_markers,
)


def test_page_markers_and_figure_references_are_found_in_order():
    text = "<!--page:3-->a ![cap](figure:7)\n<!-- page: 4 -->b ![x](figure:2)"

    assert find_page_markers(text) == [3, 4]
    assert find_figure_references(text) == [7, 2]


def test_a_marker_inside_a_line_is_removed_where_it_stood():
    stripped, marks = strip_page_markers("<!--page:0-->one two <!--page:1-->three")

    assert stripped == "one two three"
    assert marks == [PageMark(0, 0), PageMark(8, 1)]


def test_a_marker_on_its_own_line_takes_the_line_with_it():
    stripped, marks = strip_page_markers("first line\n<!--page:1-->\nsecond line\n")

    # the paragraph stays one paragraph: no blank line is left behind
    assert stripped == "first line\nsecond line\n"
    assert marks == [PageMark(11, 1)]


def test_the_continuation_markers_are_taken_off_either_end():
    split = split_continuation(
        "  <!--continues-previous--><!--page:3-->text\n<!--continued-by-next-->\n"
    )

    assert split.body == "<!--page:3-->text"
    assert split.continues_previous
    assert split.continued_by_next


def test_a_marker_in_the_middle_is_not_a_continuation():
    split = split_continuation("<!--page:3-->a <!--continued-by-next--> b")

    assert not split.continued_by_next
    assert not split.continues_previous


def test_the_leading_page_markers_are_split_off():
    assert split_leading_page_markers("\n<!--page:4-->\n<!-- page:5 -->rest") == (
        "<!--page:4--><!--page:5-->",
        "rest",
    )
    assert split_leading_page_markers("rest<!--page:4-->") == ("", "rest<!--page:4-->")
