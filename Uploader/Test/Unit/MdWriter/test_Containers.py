"""Tests for the fences of the note blocks being checked and joined."""

from OcrModule.MdWriter.Containers import (
    closing_container,
    drop_closing_fence,
    drop_opening_fence,
    fence_problems,
    opening_container,
)


def test_balanced_blocks_pass():
    assert fence_problems(":::column\na\n:::\n\ntext\n\n::: sidenote\nb\n:::") == []


def test_a_stray_close_an_unclosed_block_and_nesting_are_reported():
    assert "closes no block" in fence_problems("text\n:::")[0]
    assert "never closed" in fence_problems(":::column\na")[0]
    assert "never nest" in fence_problems(":::column\n:::sidenote\n:::")[0]


def test_the_block_a_text_ends_by_closing_is_found():
    assert closing_container("x\n:::column\na\n:::\n") == "column"
    assert closing_container(":::column\na\n:::\n\nafter") is None


def test_the_block_a_text_starts_by_opening_is_found():
    assert opening_container("\n:::sidenote\nb\n:::") == "sidenote"
    assert opening_container("b\n:::sidenote") is None


def test_the_fences_at_a_join_are_dropped():
    assert drop_closing_fence(":::column\na\n:::\n") == ":::column\na"
    assert drop_opening_fence("\n:::column\nb\n:::") == "b\n:::"
