"""Tests for joining the two halves of a text a page break split."""

from OcrModule.TextJoin import join_separator, join_texts


def test_ascii_halves_are_joined_with_a_space():
    assert join_texts("the end of a \n", "  sentence") == "the end of a sentence"


def test_cjk_halves_are_joined_directly():
    assert join_texts("日本語の\n", "文章") == "日本語の文章"


def test_a_hyphenated_word_is_joined_with_its_hyphen_kept():
    assert join_texts("pipe-", "line") == "pipe-line"


def test_an_empty_half_needs_no_separator():
    assert join_separator("", "text") == ""
    assert join_separator("text", "  ") == ""


def test_the_separator_looks_past_the_whitespace_at_the_join():
    assert join_separator("word  ", "\nword") == " "
