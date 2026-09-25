"""Joining the Markdown of every page into the one document it is part of."""

from collections.abc import Sequence

from ..TextJoin import join_separator
from .Containers import (
    closing_container,
    drop_closing_fence,
    drop_opening_fence,
    opening_container,
)
from .Markers import (
    FIGURE_REFERENCE_PATTERN,
    page_marker,
    split_leading_page_markers,
    without_page_markers,
)

# What separates two parts that do not share a paragraph.
PARAGRAPH_BREAK = "\n\n"


def stitch(bodies: Sequence[str], joins: Sequence[bool]) -> str:
    """The whole document's Markdown, the pages joined in order.

    Each page is put after its page marker. Where a page turn splits a
    paragraph, the two halves are joined into one paragraph, and a note block
    both pages hold it in into one block. Everywhere else, pages are separated
    by a blank line.

    Args:
        bodies: Every page's Markdown, continuation markers taken off, in order.
        joins: Whether each page's last paragraph runs on into the next page;
            one fewer than there are pages.
    """
    document = ""

    for page_index, body in enumerate(bodies):
        continues = page_index > 0 and joins[page_index - 1]
        document = _append(
            document, f"{page_marker(page_index)}{body.strip()}", continues
        )

    return document


def _append(document: str, part: str, continues_paragraph: bool) -> str:
    """The document with the part after it, as one paragraph or after a break."""
    if not document:
        return part

    if not continues_paragraph:
        return f"{document.rstrip()}{PARAGRAPH_BREAK}{part}"

    # the part opens with its page marker, so the text after it decides the join
    markers, rest = split_leading_page_markers(part)

    # a figure at the join stands between the halves; it goes after the paragraph
    former, trailing = _split_trailing_figures(document.rstrip())
    rest, leading = _split_leading_figures(rest)
    rest = _after_first_paragraph(rest, trailing + leading)

    closed = closing_container(without_page_markers(former))
    opened = opening_container(rest)

    # a note block each part closed and reopened at the join is one block
    if closed is not None and closed == opened:
        former, rest = drop_closing_fence(former), drop_opening_fence(rest)
    # a paragraph cannot run across a fence, so the join is a break after all
    elif closed is not None or opened is not None:
        return f"{document.rstrip()}{PARAGRAPH_BREAK}{part}"

    separator = join_separator(without_page_markers(former), rest)

    return f"{former}{separator}{markers}{rest.lstrip()}"


def _is_figure(paragraph: str) -> bool:
    """Whether a paragraph is one figure and nothing else."""
    return FIGURE_REFERENCE_PATTERN.fullmatch(paragraph.strip()) is not None


def _split_trailing_figures(text: str) -> tuple[str, list[str]]:
    """The text without the figure paragraphs it ends with, and those figures."""
    paragraphs = text.split(PARAGRAPH_BREAK)
    figures: list[str] = []

    while len(paragraphs) > 1 and _is_figure(paragraphs[-1]):
        figures.insert(0, paragraphs.pop().strip())

    return PARAGRAPH_BREAK.join(paragraphs).rstrip(), figures


def _split_leading_figures(text: str) -> tuple[str, list[str]]:
    """The text without the figure paragraphs it starts with, and those figures."""
    paragraphs = text.strip().split(PARAGRAPH_BREAK)
    figures: list[str] = []

    while len(paragraphs) > 1 and _is_figure(paragraphs[0]):
        figures.append(paragraphs.pop(0).strip())

    return PARAGRAPH_BREAK.join(paragraphs).lstrip(), figures


def _after_first_paragraph(text: str, figures: list[str]) -> str:
    """The text with the figures put after its first paragraph."""
    if not figures:
        return text

    first, _, after = text.partition(PARAGRAPH_BREAK)
    return PARAGRAPH_BREAK.join([first, *figures, *([after] if after else [])])
