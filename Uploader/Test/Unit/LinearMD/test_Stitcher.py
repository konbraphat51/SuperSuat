"""Tests for the parts of every batch being joined into one document."""

from OcrModule.LinearMD.Schema import PageBatch
from OcrModule.LinearMD.Stitcher import stitch

E0 = PageBatch(index=0, first_page=0, last_page=2, written_pages=(0, 1, 2))
F1 = PageBatch(index=1, first_page=2, last_page=4, written_pages=(3,))
E2 = PageBatch(index=2, first_page=4, last_page=5, written_pages=(4, 5))


def test_parts_that_share_no_paragraph_are_separated_by_a_blank_line():
    document = stitch(
        [
            (E0, "<!--page:0-->a\n"),
            (F1, "<!--page:3-->b"),
            (E2, "\n<!--page:4-->c"),
        ]
    )

    assert document == "<!--page:0-->a\n\n<!--page:3-->b\n\n<!--page:4-->c"


def test_ascii_paragraphs_continued_across_parts_are_joined_with_a_space():
    document = stitch(
        [
            (E0, "<!--page:0-->the end of"),
            (
                F1,
                "<!--continues-previous-->\n<!--page:3-->a sentence "
                "that runs on<!--continued-by-next-->",
            ),
            (E2, "<!--page:4-->into the next part."),
        ]
    )

    assert document == (
        "<!--page:0-->the end of <!--page:3-->a sentence that runs on "
        "<!--page:4-->into the next part."
    )


def test_cjk_paragraphs_continued_across_parts_are_joined_directly():
    document = stitch(
        [
            (E0, "<!--page:0-->文章の"),
            (F1, "<!--continues-previous--><!--page:3-->続き"),
            (E2, "<!--page:4-->次"),
        ]
    )

    assert document == "<!--page:0-->文章の<!--page:3-->続き\n\n<!--page:4-->次"


def test_a_single_part_is_the_document():
    assert stitch([(E0, "  <!--page:0-->a  ")]) == "<!--page:0-->a"


def test_a_box_closed_and_reopened_at_a_continued_join_is_one_box():
    document = stitch(
        [
            (E0, "<!--page:0-->:::column\n箱の中の\n:::"),
            (
                F1,
                "<!--continues-previous--><!--page:3-->\n:::column\n続き\n:::\n"
                "<!--continued-by-next-->",
            ),
            (E2, "<!--page:4-->\n:::column\nさらに続く\n:::"),
        ]
    )

    assert document == (
        "<!--page:0-->:::column\n箱の中の<!--page:3-->続き<!--page:4-->さらに続く\n:::"
    )


def test_boxes_of_different_kinds_are_not_merged():
    document = stitch(
        [
            (E0, "<!--page:0-->:::column\na\n:::"),
            (F1, "<!--continues-previous--><!--page:3-->\n:::sidenote\nb\n:::"),
        ]
    )

    assert document == (
        "<!--page:0-->:::column\na\n:::\n\n<!--page:3-->\n:::sidenote\nb\n:::"
    )
