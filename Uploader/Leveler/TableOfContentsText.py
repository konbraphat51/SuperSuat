"""The tables of contents printed in a document, written out as text for the leveler model."""

from OcrModule.OcrSchema import (
    OcrResultBlock,
    OcrResultBlockTableOfContents,
    TableOfContentsEntry,
)

# How far each nesting level of entries is indented.
INDENT = "  "


def collect_tables_of_contents(
    blocks: list[OcrResultBlock],
) -> list[OcrResultBlockTableOfContents]:
    """Every table of contents block of the document, in document order."""
    return [
        block for block in blocks if isinstance(block, OcrResultBlockTableOfContents)
    ]


def table_of_contents_text(tables: list[OcrResultBlockTableOfContents]) -> str:
    """Every table of contents as indented `number | title | page` lines, each
    under a line naming the block and the pages it is printed on.

    An empty string when there is none.

    Args:
        tables: The table of contents blocks, in document order.
    """
    return "\n\n".join(_table_text(table) for table in tables)


def _table_text(table: OcrResultBlockTableOfContents) -> str:
    """One table of contents, under a line saying where it is printed."""
    lines = [f"Table of contents block {table.block_index}{_pages_label(table)}:"]
    lines += _entry_lines(table.entries, depth=0)
    return "\n".join(lines)


def _entry_lines(entries: list[TableOfContentsEntry], depth: int) -> list[str]:
    """The entries and those nested under them, one line each."""
    lines: list[str] = []

    for entry in entries:
        fields = (entry.section_number or "", entry.title, entry.page_number or "")
        lines.append(f"{INDENT * depth}- {' | '.join(fields).strip()}")
        lines += _entry_lines(entry.children, depth + 1)

    return lines


def _pages_label(table: OcrResultBlockTableOfContents) -> str:
    """Where the table is printed, as ", printed on page 3" or "pages 3-4"."""
    if not table.existing_pages:
        return ""

    first = min(table.existing_pages) + 1
    last = max(table.existing_pages) + 1
    if first == last:
        return f", printed on page {first}"
    return f", printed on pages {first}-{last}"
