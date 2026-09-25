"""Reading the stitched Markdown back into the document tree."""

import logging
import re
from bisect import bisect_right
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from itertools import count

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.container import container_plugin
from mdit_py_plugins.dollarmath import dollarmath_plugin

from ..OcrSchema import (
    TEXT_BLOCK_TYPES,
    OcrResult,
    OcrResultBlock,
    OcrResultBlockFigure,
    OcrResultBlockText,
    OcrResultSection,
)
from .Containers import NOTE_CONTAINERS
from .Markers import PageMark, strip_page_markers
from .Schema import DetectedFigure

logger = logging.getLogger(__name__)

# The document itself, which every section hangs under.
ROOT_BLOCK_INDEX = 0

# Where a figure placed by the model points, as `![caption](figure:ID)`.
FIGURE_SOURCE_PATTERN = re.compile(r"^figure:(\d+)$")

# A footnote's definition, `[^n]: note text`, opening a paragraph.
FOOTNOTE_DEFINITION_PATTERN = re.compile(r"^\[\^[^\]\s]+\]:")

# What each top-level Markdown block is written down as, when it is not
# anything more particular; blocks missing here are left out.
BLOCK_TYPES: dict[str, TEXT_BLOCK_TYPES] = {
    "paragraph_open": "paragraph",
    "bullet_list_open": "paragraph",
    "ordered_list_open": "paragraph",
    "blockquote_open": "paragraph",
    "html_block": "paragraph",
    "heading_open": "heading",
    "fence": "code",
    "code_block": "code",
    "math_block": "math",
    "math_block_label": "math",
    "table_open": "table",
    **{f"container_{name}_open": "note" for name in NOTE_CONTAINERS},
}


@dataclass
class _Entry:
    """One block of the document, before it is given its place in the tree."""

    pages: list[int]
    block_type: TEXT_BLOCK_TYPES | None = None  # None for a figure
    text: str = ""
    figure: DetectedFigure | None = None
    caption: str = ""


@dataclass
class _SourceMap:
    """Finding the pages of a stretch of the marker-free Markdown."""

    text: str
    marks: list[PageMark]
    line_offsets: list[int] = field(init=False)

    def __post_init__(self) -> None:
        offsets = [0]
        for line in self.text.splitlines(keepends=True):
            offsets.append(offsets[-1] + len(line))
        self.line_offsets = offsets

    def lines(self, first: int, last: int) -> str:
        """The source of lines [first, last), as it is."""
        return self.text[self._offset(first) : self._offset(last)]

    def pages(self, first: int, last: int) -> list[int]:
        """The pages lines [first, last) are on: the page they start on, and
        every page that starts inside them."""
        start, end = self._offset(first), self._offset(last)
        mark_offsets = [mark.offset for mark in self.marks]

        opening = bisect_right(mark_offsets, start) - 1
        pages = {self.marks[opening].page_index if opening >= 0 else 0}

        for mark in self.marks[opening + 1 :]:
            if mark.offset >= end:
                break
            # a page that starts after the block's last text holds none of it
            if self.text[mark.offset : end].strip():
                pages.add(mark.page_index)

        return sorted(pages)

    def _offset(self, line: int) -> int:
        """The offset line `line` starts at, or the end of the text past it."""
        return self.line_offsets[min(line, len(self.line_offsets) - 1)]


def parse_markdown(markdown: str, figures: Sequence[DetectedFigure]) -> OcrResult:
    """The document tree the Markdown describes.

    Every heading opens a section under the root, holding the blocks up to the
    next heading. A figure the Markdown places is put where it is placed;
    a detected figure it never places is put after the last block of its page.

    Args:
        markdown: The whole document, as the pages were stitched into.
        figures: Every figure detected in the document.
    """
    source, marks = strip_page_markers(markdown)
    source_map = _SourceMap(source, marks)
    entries = _read_entries(_parser().parse(source), source_map, figures)
    entries = _place_unreferenced_figures(entries, figures)

    return OcrResult(root_section=_build_tree(entries))


def _parser() -> MarkdownIt:
    """A Markdown parser for the syntax the model is asked to write.

    Link reference definitions are off: `[^1]: note` would otherwise be read as
    one and disappear. Footnote definitions are found by the pattern instead,
    since two parts may well reuse a footnote label.
    """
    parser = (
        MarkdownIt("commonmark")
        .enable("table")
        .disable("reference")
        .use(dollarmath_plugin)
    )
    for name in NOTE_CONTAINERS:
        parser.use(container_plugin, name=name)
    return parser


def _read_entries(
    tokens: list[Token],
    source_map: _SourceMap,
    figures: Sequence[DetectedFigure],
) -> list[_Entry]:
    """Every top-level block of the parsed Markdown, in document order."""
    figures_by_id = {figure.block_id: figure for figure in figures}
    placed: set[int] = set()
    entries: list[_Entry] = []

    for index, token in enumerate(tokens):
        if token.level != 0 or token.map is None or token.nesting == -1:
            continue

        block_type = BLOCK_TYPES.get(token.type)
        if block_type is None:
            continue

        first, last = token.map
        pages = source_map.pages(first, last)
        text = _block_text(token, tokens, index, source_map)

        if token.type == "html_block" and _is_comment(text):
            continue

        if token.type == "paragraph_open":
            inline = tokens[index + 1]
            figure_id = _placed_figure_id(inline)

            if figure_id is not None:
                figure_entry = _figure_entry(figure_id, inline, figures_by_id, placed)
                if figure_entry is not None:
                    entries.append(figure_entry)
                continue

            if FOOTNOTE_DEFINITION_PATTERN.match(text):
                block_type = "note"

        if text:
            entries.append(_Entry(pages=pages, block_type=block_type, text=text))

    return entries


def _block_text(
    token: Token,
    tokens: list[Token],
    index: int,
    source_map: _SourceMap,
) -> str:
    """What the block's text is written down as."""
    assert token.map is not None
    first, last = token.map

    if token.type == "heading_open":
        return tokens[index + 1].content.strip()

    if token.type in ("fence", "code_block", "math_block", "math_block_label"):
        return token.content.strip()

    if token.type.startswith("container_"):
        # the map covers the opening fence but not the closing one
        return source_map.lines(first + 1, last).strip()

    return source_map.lines(first, last).strip()


def _figure_entry(
    figure_id: int,
    inline: Token,
    figures_by_id: dict[int, DetectedFigure],
    placed: set[int],
) -> _Entry | None:
    """The figure a paragraph places, or None if it cannot be placed there."""
    figure = figures_by_id.get(figure_id)

    if figure is None:
        logger.warning(
            "figure %d is placed but was never detected, so it is dropped", figure_id
        )
        return None

    if figure_id in placed:
        logger.warning("figure %d is placed twice; only the first is kept", figure_id)
        return None

    placed.add(figure_id)
    image = next(child for child in inline.children or [] if child.type == "image")

    return _Entry(
        pages=[figure.page_index],
        figure=figure,
        caption=image.content.strip(),
    )


def _placed_figure_id(inline: Token) -> int | None:
    """The figure id of a paragraph that is one figure image, or None."""
    children = [
        child
        for child in inline.children or []
        if not (
            child.type in ("softbreak", "hardbreak")
            or (child.type == "text" and not child.content.strip())
        )
    ]

    if len(children) != 1 or children[0].type != "image":
        return None

    match = FIGURE_SOURCE_PATTERN.match(str(children[0].attrs.get("src", "")).strip())
    return int(match.group(1)) if match else None


def _is_comment(text: str) -> bool:
    """Whether an HTML block is nothing but comments, which hold no text."""
    return not re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()


def _place_unreferenced_figures(
    entries: list[_Entry],
    figures: Sequence[DetectedFigure],
) -> list[_Entry]:
    """The entries with every detected figure the Markdown never placed put
    after the last block of its page."""
    placed = {entry.figure.block_id for entry in entries if entry.figure is not None}
    kept = list(entries)

    for figure in figures:
        if figure.block_id in placed:
            continue

        logger.warning(
            "figure %d on page %d is never placed, so it goes after the page's last block",
            figure.block_id,
            figure.page_index,
        )
        kept.insert(
            _insertion_point(kept, figure.page_index),
            _Entry(pages=[figure.page_index], figure=figure),
        )

    return kept


def _insertion_point(entries: list[_Entry], page_index: int) -> int:
    """Where a block of the page goes: after the last block on it, or else
    before the first block of a later page."""
    on_page = [i for i, entry in enumerate(entries) if page_index in entry.pages]
    if on_page:
        return on_page[-1] + 1

    later = [
        i
        for i, entry in enumerate(entries)
        if entry.pages and min(entry.pages) > page_index
    ]
    return later[0] if later else len(entries)


def _build_tree(entries: list[_Entry]) -> OcrResultSection:
    """The document tree of the entries: a section under the root per heading."""
    block_indices = count(ROOT_BLOCK_INDEX + 1)
    root = OcrResultSection(
        block_type="section",
        existing_pages=[],
        block_index=ROOT_BLOCK_INDEX,
        section_content=[],
    )
    current = root

    for entry in entries:
        if entry.block_type == "heading":
            current = OcrResultSection(
                block_type="section",
                existing_pages=[],
                block_index=next(block_indices),
                section_content=[],
            )
            root.section_content.append(current)

        current.section_content.append(_to_block(entry, block_indices))

    root.recompute_existing_pages()
    return root


def _to_block(entry: _Entry, block_indices: Iterator[int]) -> OcrResultBlock:
    """The entry as the document tree holds it."""
    if entry.figure is not None:
        return OcrResultBlockFigure(
            block_type="figure",
            existing_pages=[entry.figure.page_index],
            block_index=next(block_indices),
            page_index=entry.figure.page_index,
            bounding_box=entry.figure.bounding_box,
            caption=entry.caption,
        )

    assert entry.block_type is not None
    return OcrResultBlockText(
        block_type=entry.block_type,
        existing_pages=entry.pages,
        block_index=next(block_indices),
        text=entry.text,
    )
