"""The headings of a document as the leveler model is asked about them, and the answers it gives."""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from OcrModule.OcrSchema import OcrResultBlock, OcrResultBlockText

from .LevelerSchema import HeadingLevel

# The block_type of a block that opens a section.
HEADING_BLOCK_TYPE = "heading"

# The level of the document's own title, which nothing sits above.
TOP_HEADING_LEVEL = 1


@dataclass
class Heading:
    """One heading of the document, as the model is asked about it."""

    block_index: int
    page_index: int | None  # the first page it is printed on, if known
    text: str


# Headings grouped by the page they are printed on, in document order.
PageHeadings = list[tuple[int | None, list[Heading]]]

# The parts of a message's content, as a chat model takes them.
Content = list[str | dict[Any, Any]]


def collect_headings(blocks: list[OcrResultBlock]) -> list[Heading]:
    """Every heading of the document, in document order."""
    return [
        Heading(
            block_index=block.block_index,
            page_index=min(block.existing_pages) if block.existing_pages else None,
            text=block.text,
        )
        for block in blocks
        if isinstance(block, OcrResultBlockText)
        and block.block_type == HEADING_BLOCK_TYPE
    ]


def group_by_page(headings: list[Heading]) -> PageHeadings:
    """Each run of headings printed on the same page, in document order."""
    grouped: PageHeadings = []

    for heading in headings:
        if grouped and grouped[-1][0] == heading.page_index:
            grouped[-1][1].append(heading)
        else:
            grouped.append((heading.page_index, [heading]))

    return grouped


def split_into_parts(page_headings: PageHeadings, max_pages: int) -> list[PageHeadings]:
    """The heading pages in runs of at most `max_pages`, in order."""
    return [
        page_headings[start : start + max_pages]
        for start in range(0, len(page_headings), max_pages)
    ]


def headings_json(headings: list[Heading], levels: dict[int, float] | None) -> str:
    """The headings as JSON, with their levels when `levels` is given."""
    listed: list[dict[str, object]] = []

    for heading in headings:
        entry: dict[str, object] = {"block_id": heading.block_index}
        if heading.page_index is not None:
            entry["page_number"] = heading.page_index + 1
        entry["text"] = heading.text
        if levels is not None:
            entry["heading_level"] = format_level(levels[heading.block_index])
        listed.append(entry)

    return json.dumps(listed, ensure_ascii=False, separators=(",", ":"))


def format_level(level: float) -> int | float:
    """A level as the model wrote it: 2 rather than 2.0, 2.5 as it is."""
    return int(level) if float(level).is_integer() else level


def apply_levels(
    answered: Sequence[HeadingLevel],
    headings: list[Heading],
    levels: dict[int, float],
) -> list[str]:
    """Records each answered level into `levels`, and reports what could not
    be recorded."""
    asked_ids = {heading.block_index for heading in headings}
    problems: list[str] = []

    for level in answered:
        if level.target_block_id not in asked_ids:
            problems.append(
                f"Block {level.target_block_id} is not one of the headings you "
                "were asked about, so it was ignored."
            )
            continue

        if level.heading_level < TOP_HEADING_LEVEL:
            problems.append(
                f"Block {level.target_block_id} was given level "
                f"{format_level(level.heading_level)}; the document's own title "
                f"is level {TOP_HEADING_LEVEL} and nothing sits above it."
            )
            continue

        levels[level.target_block_id] = level.heading_level

    return problems


def retry_message(problems: list[str], unleveled: list[Heading]) -> str:
    """What the model is told when its answer did not cover every heading."""
    lines = [f"- {problem}" for problem in problems]

    if unleveled:
        lines.append(
            f"- These headings still have no level: {list_ids(unleveled)}. "
            "Give each one the level it holds in the hierarchy you just described."
        )

    return (
        "Every level you gave that could be used has been recorded, and the "
        "hierarchy you described stands. Answer again for what is still "
        "missing, keeping the levels you already gave:\n" + "\n".join(lines)
    )


def text_part(text: str) -> dict[str, str]:
    """A text part of a message's content."""
    return {"type": "text", "text": text}


def list_ids(headings: list[Heading]) -> str:
    """The headings' block ids as one comma-separated list."""
    return ", ".join(str(heading.block_index) for heading in headings)
