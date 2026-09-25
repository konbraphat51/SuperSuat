"""Tests for the parts of every page being joined into one document."""

from OcrModule.MdWriter.Schema import PageTask
from OcrModule.MdWriter.Stitcher import stitch

P0, P1, P2 = PageTask(0), PageTask(1), PageTask(2)


def test_parts_that_share_no_paragraph_are_separated_by_a_blank_line():
    document = stitch([(P0, "a\n"), (P1, "b"), (P2, "\nc")])

    assert document == "<!--page:0-->a\n\n<!--page:1-->b\n\n<!--page:2-->c"


def test_ascii_paragraphs_continued_across_pages_are_joined_with_a_space():
    document = stitch(
        [
            (P0, "the end of"),
            (
                P1,
                "<!--continues-previous-->\na sentence "
                "that runs on<!--continued-by-next-->",
            ),
            (P2, "into the next page."),
        ]
    )

    assert document == (
        "<!--page:0-->the end of <!--page:1-->a sentence that runs on "
        "<!--page:2-->into the next page."
    )


def test_cjk_paragraphs_continued_across_pages_are_joined_directly():
    document = stitch(
        [
            (P0, "文章の"),
            (P1, "<!--continues-previous-->続き"),
            (P2, "次"),
        ]
    )

    assert document == "<!--page:0-->文章の<!--page:1-->続き\n\n<!--page:2-->次"


def test_a_single_part_is_the_document():
    assert stitch([(P0, "  a  ")]) == "<!--page:0-->a"


def test_a_blank_page_keeps_its_marker():
    assert stitch([(P0, "a"), (P1, "")]) == "<!--page:0-->a\n\n<!--page:1-->"


def test_a_box_closed_and_reopened_at_a_continued_join_is_one_box():
    document = stitch(
        [
            (P0, ":::column\n箱の中の\n:::"),
            (
                P1,
                "<!--continues-previous-->\n:::column\n続き\n:::\n"
                "<!--continued-by-next-->",
            ),
            (P2, ":::column\nさらに続く\n:::"),
        ]
    )

    assert document == (
        "<!--page:0-->:::column\n箱の中の<!--page:1-->続き<!--page:2-->さらに続く\n:::"
    )


def test_boxes_of_different_kinds_are_not_merged():
    document = stitch(
        [
            (P0, ":::column\na\n:::"),
            (P1, "<!--continues-previous-->\n:::sidenote\nb\n:::"),
        ]
    )

    assert document == (
        "<!--page:0-->:::column\na\n:::\n\n<!--page:1-->:::sidenote\nb\n:::"
    )
