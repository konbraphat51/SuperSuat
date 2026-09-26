"""Tests for the pages being joined into one document."""

from OcrModule.MdWriter.Assembly.Stitcher import stitch


def test_pages_that_share_no_paragraph_are_separated_by_a_blank_line():
    document = stitch(["a\n", "b", "\nc"], [False, False])

    assert document == "<!--page:0-->a\n\n<!--page:1-->b\n\n<!--page:2-->c"


def test_ascii_paragraphs_continued_across_pages_are_joined_with_a_space():
    document = stitch(
        ["the end of", "a sentence that runs on", "into the next page."],
        [True, True],
    )

    assert document == (
        "<!--page:0-->the end of <!--page:1-->a sentence that runs on "
        "<!--page:2-->into the next page."
    )


def test_cjk_paragraphs_continued_across_pages_are_joined_directly():
    document = stitch(["文章の", "続き", "次"], [True, False])

    assert document == "<!--page:0-->文章の<!--page:1-->続き\n\n<!--page:2-->次"


def test_a_single_page_is_the_document():
    assert stitch(["  a  "], []) == "<!--page:0-->a"


def test_a_blank_page_keeps_its_marker():
    assert stitch(["a", ""], [False]) == "<!--page:0-->a\n\n<!--page:1-->"


def test_a_box_closed_and_reopened_at_a_continued_join_is_one_box():
    document = stitch(
        [
            ":::column\nin the box\n:::",
            ":::column\nthe text\n:::",
            ":::column\ngoes on\n:::",
        ],
        [True, True],
    )

    assert document == (
        "<!--page:0-->:::column\nin the box <!--page:1-->the text "
        "<!--page:2-->goes on\n:::"
    )


def test_boxes_of_different_kinds_are_not_merged():
    document = stitch([":::column\na\n:::", ":::sidenote\nb\n:::"], [True])

    assert document == (
        "<!--page:0-->:::column\na\n:::\n\n<!--page:1-->:::sidenote\nb\n:::"
    )


def test_a_figure_opening_the_continued_page_goes_after_the_joined_paragraph():
    document = stitch(["the text", "![a](figure:0)\n\nruns on\n\nnext"], [True])

    assert document == (
        "<!--page:0-->the text <!--page:1-->runs on\n\n![a](figure:0)\n\nnext"
    )


def test_a_figure_ending_the_page_before_goes_after_the_joined_paragraph():
    document = stitch(["before\n\nthe text\n\n![a](figure:0)", "runs on"], [True])

    assert document == (
        "<!--page:0-->before\n\nthe text <!--page:1-->runs on\n\n![a](figure:0)"
    )


def test_a_figure_whose_caption_holds_brackets_still_moves_after_the_join():
    document = stitch(["the text", "![interval [a, b]](figure:0)\n\nruns on"], [True])

    assert document == (
        "<!--page:0-->the text <!--page:1-->runs on\n\n![interval [a, b]](figure:0)"
    )
