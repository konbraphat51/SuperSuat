"""The markers the model writes into its Markdown, and taking them back out."""

import re
from dataclasses import dataclass

# Where a page starts, put by the stitcher before the Markdown of each page.
PAGE_MARKER_PATTERN = re.compile(r"<!--\s*page:\s*(\d+)\s*-->")

# A fill page's first paragraph continues the previous page's last one.
CONTINUES_PREVIOUS_MARKER = "<!--continues-previous-->"
CONTINUES_PREVIOUS_PATTERN = re.compile(r"<!--\s*continues-previous\s*-->")

# A fill page's last paragraph is continued by the next page's first one.
CONTINUED_BY_NEXT_MARKER = "<!--continued-by-next-->"
CONTINUED_BY_NEXT_PATTERN = re.compile(r"<!--\s*continued-by-next\s*-->")

# What the model answers alone for a page that holds nothing to transcribe.
BLANK_PAGE_MARKER = "<!--blank-page-->"
BLANK_PAGE_PATTERN = re.compile(r"<!--\s*blank-page\s*-->")

# A figure placed by its detected id, as `![caption](figure:ID)`.
FIGURE_REFERENCE_PATTERN = re.compile(r"!\[[^\]]*\]\(\s*figure:(\d+)\s*\)")

# Page markers at the very start of a text, with the whitespace around them.
_LEADING_PAGE_MARKERS = re.compile(rf"^(?:\s*{PAGE_MARKER_PATTERN.pattern})+\s*")


@dataclass(frozen=True)
class PageMark:
    """Where a page started, in a text the page markers were taken out of.

    Attributes:
        offset: The character offset in the stripped text the marker stood at.
        page_index: The page that starts there, 0-indexed.
    """

    offset: int
    page_index: int


@dataclass(frozen=True)
class ContinuationSplit:
    """A fill page's output with its continuation markers taken off.

    Attributes:
        body: The Markdown without the markers.
        continues_previous: Whether it opened with CONTINUES_PREVIOUS_MARKER.
        continued_by_next: Whether it closed with CONTINUED_BY_NEXT_MARKER.
    """

    body: str
    continues_previous: bool
    continued_by_next: bool


def page_marker(page_index: int) -> str:
    """The marker the model writes where page `page_index` starts."""
    return f"<!--page:{page_index}-->"


def find_page_markers(text: str) -> list[int]:
    """The pages of every page marker in the text, in the order they appear."""
    return [int(match.group(1)) for match in PAGE_MARKER_PATTERN.finditer(text)]


def is_blank_page(text: str) -> bool:
    """Whether the text is the blank page marker and nothing else."""
    return BLANK_PAGE_PATTERN.fullmatch(text.strip()) is not None


def find_figure_references(text: str) -> list[int]:
    """The figure ids the text places, in the order they appear."""
    return [int(match.group(1)) for match in FIGURE_REFERENCE_PATTERN.finditer(text)]


def strip_page_markers(text: str) -> tuple[str, list[PageMark]]:
    """The text without its page markers, and where each of them stood.

    A marker on a line of its own takes the line with it, so a marker the
    model put between two lines of a paragraph does not split the paragraph.
    """
    stripped: list[str] = []
    marks: list[PageMark] = []
    length = 0

    for line in text.splitlines(keepends=True):
        matches = list(PAGE_MARKER_PATTERN.finditer(line))

        if not matches:
            stripped.append(line)
            length += len(line)
            continue

        remainder = PAGE_MARKER_PATTERN.sub("", line)

        # a line holding nothing but markers goes, newline and all
        if not remainder.strip():
            marks += [PageMark(length, int(match.group(1))) for match in matches]
            continue

        removed = 0
        for match in matches:
            marks.append(
                PageMark(length + match.start() - removed, int(match.group(1)))
            )
            removed += match.end() - match.start()

        stripped.append(remainder)
        length += len(remainder)

    return "".join(stripped), marks


def split_continuation(text: str) -> ContinuationSplit:
    """The output of a fill page, its continuation markers taken off either end."""
    body = text.strip()

    leading = CONTINUES_PREVIOUS_PATTERN.match(body)
    if leading:
        body = body[leading.end() :].lstrip()

    trailing = _match_at_end(CONTINUED_BY_NEXT_PATTERN, body)
    if trailing:
        body = body[: trailing.start()].rstrip()

    return ContinuationSplit(
        body=body,
        continues_previous=leading is not None,
        continued_by_next=trailing is not None,
    )


def split_leading_page_markers(text: str) -> tuple[str, str]:
    """The page markers the text opens with, and the text after them."""
    match = _LEADING_PAGE_MARKERS.match(text)

    if match is None:
        return "", text

    markers = "".join(page_marker(page) for page in find_page_markers(match.group(0)))
    return markers, text[match.end() :]


def without_page_markers(text: str) -> str:
    """The text with every page marker removed, for looking at what is left."""
    return PAGE_MARKER_PATTERN.sub("", text)


def _match_at_end(pattern: re.Pattern[str], text: str) -> re.Match[str] | None:
    """The last match of the pattern, if it ends the text."""
    matches = list(pattern.finditer(text))

    if matches and matches[-1].end() == len(text):
        return matches[-1]

    return None
