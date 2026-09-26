"""Tests for a page's Markdown being compared with its reference text."""

from OcrModule.MdWriter.Transcriber.Agreement import agreement


def test_markdown_syntax_and_punctuation_do_not_count():
    markdown = "## 見出し\n\n本文、です。<!--continued-by-next-->"

    assert agreement(markdown, "見出し\n本文です") == 1.0


def test_a_figure_counts_by_its_caption():
    assert agreement("![図1 猫の写真](figure:0)", "図1 猫の写真") == 1.0


def test_invented_text_lowers_the_agreement():
    assert agreement("第五十一回の選挙の結果", "第五十一回の選挙") < 0.9


def test_two_empty_pages_agree():
    assert agreement("", "") == 1.0
