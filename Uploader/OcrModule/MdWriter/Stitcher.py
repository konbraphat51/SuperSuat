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
    page_marker,
    split_continuation,
    split_leading_page_markers,
    without_page_markers,
)
from .Schema import PageTask

# What separates two parts that do not share a paragraph.
PARAGRAPH_BREAK = "\n\n"


def stitch(parts: Sequence[tuple[PageTask, str]]) -> str:
    """The whole document's Markdown, the pages' parts joined in order.

    Each part is put after its page marker. A fill page says where its
    paragraphs continue a neighbour's, with its continuation markers; there,
    the two halves are joined into one paragraph, and a note block both parts
    hold it in into one block. Everywhere else, parts are separated by a
    blank line.

    Args:
        parts: Every page with the Markdown it returned, in document order.
    """
    document = ""
    continues_into_next = False

    for task, markdown in parts:
        if task.kind == "fill":
            split = split_continuation(markdown)
            body, continues = split.body, split.continues_previous
            continued = split.continued_by_next
        else:
            body, continues, continued = markdown.strip(), continues_into_next, False

        document = _append(document, f"{page_marker(task.page_index)}{body}", continues)
        continues_into_next = continued

    return document


def _append(document: str, part: str, continues_paragraph: bool) -> str:
    """The document with the part after it, as one paragraph or after a break."""
    if not document:
        return part

    if not continues_paragraph:
        return f"{document.rstrip()}{PARAGRAPH_BREAK}{part}"

    # the part opens with its page marker, so the text after it decides the join
    markers, rest = split_leading_page_markers(part)
    former = document.rstrip()

    closed = closing_container(without_page_markers(former))
    opened = opening_container(rest)

    # a note block each part closed and reopened at the join is one block
    if closed is not None and closed == opened:
        former, rest = drop_closing_fence(former), drop_opening_fence(rest)
    # a paragraph cannot run across a fence, so the join is a break after all
    elif closed is not None or opened is not None:
        return f"{former}{PARAGRAPH_BREAK}{part}"

    separator = join_separator(without_page_markers(former), rest)

    return f"{former}{separator}{markers}{rest.lstrip()}"
