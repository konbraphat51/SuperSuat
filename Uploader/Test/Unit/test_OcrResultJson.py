"""Tests for writing an OcrResult out as JSON and reading it back."""

import pytest

from OcrModule.OcrResultJson import dump_ocr_result, load_ocr_result
from OcrModule.OcrSchema import (
    OcrResult,
    OcrResultBlockFigure,
    OcrResultBlockTableOfContents,
    OcrResultBlockText,
    OcrResultSection,
    TableOfContentsEntry,
)


def sample_result() -> OcrResult:
    """A tree holding every kind of block, nested."""
    heading = OcrResultBlockText("heading", [0], 1, "Chapter 1")
    figure = OcrResultBlockFigure("figure", [0], 2, 0, (10, 20, 30, 40), "A figure")
    contents = OcrResultBlockTableOfContents(
        "table_of_contents",
        [1],
        3,
        [
            TableOfContentsEntry(
                "1", "Chapter 1", "1", [TableOfContentsEntry(None, "Aside", None)]
            )
        ],
    )
    chapter = OcrResultSection("section", [0, 1], 4, [heading, figure, contents])
    return OcrResult(OcrResultSection("section", [0, 1], 0, [chapter]))


def test_a_tree_reads_back_as_it_was_written():
    result = sample_result()

    assert load_ocr_result(dump_ocr_result(result)) == result


def test_text_is_written_unescaped():
    result = OcrResult(
        OcrResultSection(
            "section", [0], 0, [OcrResultBlockText("paragraph", [0], 1, "日本語")]
        )
    )

    assert "日本語" in dump_ocr_result(result)


def test_a_root_that_is_not_a_section_is_refused():
    text = '{"root_section": {"block_type": "paragraph", "existing_pages": [], "block_index": 0, "text": ""}}'

    with pytest.raises(ValueError, match="not a section"):
        load_ocr_result(text)
