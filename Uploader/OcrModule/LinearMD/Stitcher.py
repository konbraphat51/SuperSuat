"""Joining the Markdown of every batch into the one document it is part of."""

from collections.abc import Sequence

from ..TextJoin import join_separator
from .Markers import (
    split_continuation,
    split_leading_page_markers,
    without_page_markers,
)
from .Schema import PageBatch

# What separates two parts that do not share a paragraph.
PARAGRAPH_BREAK = "\n\n"


def stitch(parts: Sequence[tuple[PageBatch, str]]) -> str:
    """The whole document's Markdown, the batches' parts joined in order.

    A fill batch says where its paragraphs continue a neighbour's, with its
    continuation markers; there, the two halves are joined into one
    paragraph. Everywhere else, parts are separated by a blank line.

    Args:
        parts: Every batch with the Markdown it returned, in document order.
    """
    document = ""
    continues_into_next = False

    for batch, markdown in parts:
        if batch.kind == "fill":
            split = split_continuation(markdown)
            document = _append(document, split.body, split.continues_previous)
            continues_into_next = split.continued_by_next
        else:
            document = _append(document, markdown.strip(), continues_into_next)
            continues_into_next = False

    return document


def _append(document: str, part: str, continues_paragraph: bool) -> str:
    """The document with the part after it, as one paragraph or after a break."""
    if not document:
        return part

    if not part:
        return document

    if not continues_paragraph:
        return f"{document.rstrip()}{PARAGRAPH_BREAK}{part}"

    # the part opens with its page marker, so the text after it decides the join
    markers, rest = split_leading_page_markers(part)
    former = document.rstrip()
    separator = join_separator(without_page_markers(former), rest)

    return f"{former}{separator}{markers}{rest.lstrip()}"
