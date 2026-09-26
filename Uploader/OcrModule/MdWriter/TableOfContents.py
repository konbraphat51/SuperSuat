"""The entries the model writes in a `:::toc` block: reading them into a tree, and checking them."""

import re
from dataclasses import dataclass

from ..OcrSchema import TableOfContentsEntry
from .Containers import CLOSE_FENCE_PATTERN, TABLE_OF_CONTENTS_CONTAINER

# One entry, as `- number | title | page`, indented two spaces per level.
ENTRY_PATTERN = re.compile(r"^(?P<indent>[ \t]*)[-*+][ \t]+(?P<fields>.*?)[ \t]*$")

# A `|` that separates two fields, not one written in a title as `\|`.
FIELD_SEPARATOR_PATTERN = re.compile(r"(?<!\\)\|")

# The fields of an entry: section number, title, page number.
FIELD_COUNT = 3

# How many columns a tab indents an entry by.
TAB_WIDTH = 4

# A line opening a table of contents block, as `:::toc`.
_OPEN_FENCE_PATTERN = re.compile(
    rf"^[ \t]*:::[ \t]*{TABLE_OF_CONTENTS_CONTAINER}[ \t]*$", re.MULTILINE
)

# How much of a line that is not an entry is quoted back to the model.
QUOTED_LENGTH = 40


@dataclass(frozen=True)
class _Line:
    """One entry line, before it is given its place in the tree."""

    indent: int
    entry: TableOfContentsEntry


def parse_entries(text: str) -> list[TableOfContentsEntry]:
    """The entries of a table of contents block's inner text, nested by indentation.

    An entry indented deeper than the one before it is nested under it; lines
    that are not entries are skipped.

    Args:
        text: The lines between the `:::toc` and `:::` fences.
    """
    roots: list[TableOfContentsEntry] = []
    open_lines: list[_Line] = []

    for raw_line in text.splitlines():
        line = _read_line(raw_line)
        if line is None:
            continue

        while open_lines and open_lines[-1].indent >= line.indent:
            open_lines.pop()

        siblings = open_lines[-1].entry.children if open_lines else roots
        siblings.append(line.entry)
        open_lines.append(line)

    return roots


def entry_problems(body: str) -> list[str]:
    """Lines in a table of contents block that are not entries, as one line per problem for the model.

    Args:
        body: A page's Markdown, continuation markers taken off.
    """
    return [
        f'"{line.strip()[:QUOTED_LENGTH]}" in the :::toc block is not an entry; write '
        'each entry on a line of its own as "- number | title | page", leaving a '
        "field empty when it is not printed."
        for inner in _block_inner_texts(body)
        for line in inner.splitlines()
        if line.strip() and _read_line(line) is None
    ]


def _read_line(raw_line: str) -> _Line | None:
    """The entry a line holds, or None if it is not one."""
    match = ENTRY_PATTERN.match(raw_line.expandtabs(TAB_WIDTH))
    if match is None:
        return None

    fields = FIELD_SEPARATOR_PATTERN.split(match.group("fields"))
    if len(fields) < FIELD_COUNT:
        return None

    # a `|` the model left unescaped in a title belongs to the title
    number, *title_parts, page = (field.strip() for field in fields)
    title = "|".join(title_parts).replace(r"\|", "|").strip()
    if not title:
        return None

    return _Line(
        indent=len(match.group("indent")),
        entry=TableOfContentsEntry(
            section_number=number or None,
            title=title,
            page_number=page or None,
        ),
    )


def _block_inner_texts(body: str) -> list[str]:
    """The inner text of every table of contents block in the Markdown."""
    inner_texts: list[str] = []

    for opening in _OPEN_FENCE_PATTERN.finditer(body):
        closing = CLOSE_FENCE_PATTERN.search(body, opening.end())
        end = closing.start() if closing else len(body)
        inner_texts.append(body[opening.end() : end])

    return inner_texts
