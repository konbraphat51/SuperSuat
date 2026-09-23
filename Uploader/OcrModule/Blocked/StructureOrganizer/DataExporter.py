"""
Convert ProcessingBlocks to OcrResult
"""

import logging
from collections.abc import Iterator
from itertools import count
from typing import get_args
from ...OcrSchema import (
    TEXT_BLOCK_TYPES,
    OcrResult,
    OcrResultBlockFigure,
    OcrResultBlockText,
    OcrResultSection,
)
from .ProcessingSchema import (
    ProcessingBlock,
    ProcessingBlockText,
    ProcessingBlockTextHeading,
    ProcessingBlockFigure,
)

logger = logging.getLogger(__name__)

# What a text block the organizer never labeled is written down as.
FALLBACK_TEXT_BLOCK_TYPE = "paragraph"

# The document itself, which every section hangs under.
ROOT_BLOCK_INDEX = 0

# The level the root section sits at, below every heading.
ROOT_HEADING_LEVEL = 0


def export_processing_blocks_to_ocr_result(
    processing_blocks: list[ProcessingBlock],
) -> OcrResult:
    """Builds the document tree from the blocks, in the order they are in.

    Each heading opens a section nested by its level and holds the blocks that
    follow it, so the tree mirrors the document's own hierarchy. A figure's
    caption is folded into the figure rather than left as a block of its own.

    Args:
        processing_blocks: Every block of the document, in reading order, as
            the organizer left them.
    """
    captions, folded_block_ids = _collect_captions(processing_blocks)
    block_indices = count(ROOT_BLOCK_INDEX + 1)

    root_section = OcrResultSection(
        block_type="section",
        existing_pages=[],
        block_index=ROOT_BLOCK_INDEX,
        section_content=[],
    )
    # the sections currently open, outermost first, as (heading level, section)
    open_sections: list[tuple[int, OcrResultSection]] = [
        (ROOT_HEADING_LEVEL, root_section)
    ]

    # for each block, in reading order...
    for block in processing_blocks:
        # ...place it in the section it belongs to

        # a caption already lives in its figure
        if block.block_id in folded_block_ids:
            continue

        if isinstance(block, ProcessingBlockFigure):
            _current_section(open_sections).section_content.append(
                _to_figure_block(block, captions.get(block.block_id, ""), block_indices)
            )
            continue

        if not isinstance(block, ProcessingBlockText):
            logger.warning(
                "block %d is neither text nor figure, so it is left out", block.block_id
            )
            continue

        heading_level = _heading_level(block)

        # a heading opens the section its own content goes into
        if heading_level is not None:
            _open_section(open_sections, heading_level, block_indices)

        _current_section(open_sections).section_content.append(
            _to_text_block(block, block_indices)
        )

    _recompute_existing_pages(root_section)

    return OcrResult(root_section=root_section)


def _collect_captions(
    processing_blocks: list[ProcessingBlock],
) -> tuple[dict[int, str], set[int]]:
    """The caption text of each captioned figure, and the ids of the text
    blocks folded into them.

    A folded block is left out of the tree, since its text is in the figure
    already. A heading is never folded away: losing it would lose the section
    it opens, so it keeps its place and its text is copied.
    """
    text_blocks = {
        block.block_id: block
        for block in processing_blocks
        if isinstance(block, ProcessingBlockText)
    }

    captions: dict[int, str] = {}
    folded_block_ids: set[int] = set()

    for block in processing_blocks:
        if not isinstance(block, ProcessingBlockFigure):
            continue

        caption_block_id = block.caption_text_block_id
        if caption_block_id is None:
            continue

        caption_block = text_blocks.get(caption_block_id)
        if caption_block is None:
            logger.warning(
                "figure %d names block %d as its caption, which is not a text block "
                "of this document",
                block.block_id,
                caption_block_id,
            )
            continue

        captions[block.block_id] = caption_block.text

        if isinstance(caption_block, ProcessingBlockTextHeading):
            logger.warning(
                "figure %d is captioned by heading block %d, which stays in the document",
                block.block_id,
                caption_block_id,
            )
            continue

        folded_block_ids.add(caption_block_id)

    return captions, folded_block_ids


def _current_section(
    open_sections: list[tuple[int, OcrResultSection]],
) -> OcrResultSection:
    """The innermost section still open."""
    return open_sections[-1][1]


def _open_section(
    open_sections: list[tuple[int, OcrResultSection]],
    heading_level: int,
    block_indices: Iterator[int],
) -> None:
    """Opens a section for a heading of `heading_level`, under the innermost
    section of a lower level.

    Every section at or below that level is closed first: a heading of the
    same level starts a sibling, and one of a lower level closes everything it
    is not inside.
    """
    while (
        len(open_sections) > 1 and open_sections[-1][0] >= heading_level
    ):  # the root is never closed
        open_sections.pop()

    section = OcrResultSection(
        block_type="section",
        existing_pages=[],
        block_index=next(block_indices),
        section_content=[],
    )
    _current_section(open_sections).section_content.append(section)
    open_sections.append((heading_level, section))


def _heading_level(block: ProcessingBlockText) -> int | None:
    """The level of the heading this block is, or None if it is not one."""
    if not isinstance(block, ProcessingBlockTextHeading):
        return None

    if block.heading_level is None:
        logger.warning(
            "heading block %d has no level, so it opens no section", block.block_id
        )
        return None

    return block.heading_level


def _to_text_block(
    block: ProcessingBlockText,
    block_indices: Iterator[int],
) -> OcrResultBlockText:
    """The text block as the document tree holds it."""
    return OcrResultBlockText(
        block_type=_text_block_type(block),
        existing_pages=[block.page_index],
        block_index=next(block_indices),
        text=block.text,
    )


def _text_block_type(block: ProcessingBlockText) -> TEXT_BLOCK_TYPES:
    """The type the block was labeled with, or the fallback if it has none the
    document tree accepts."""
    if block.new_type in get_args(TEXT_BLOCK_TYPES):
        return block.new_type

    logger.warning(
        "text block %d is labeled %s, so it is written down as %s",
        block.block_id,
        block.new_type,
        FALLBACK_TEXT_BLOCK_TYPE,
    )

    return FALLBACK_TEXT_BLOCK_TYPE


def _to_figure_block(
    block: ProcessingBlockFigure,
    caption: str,
    block_indices: Iterator[int],
) -> OcrResultBlockFigure:
    """The figure as the document tree holds it, caption included."""
    return OcrResultBlockFigure(
        block_type="figure",
        existing_pages=[block.page_index],
        block_index=next(block_indices),
        page_index=block.page_index,
        bounding_box=block.bounding_box,
        caption=caption,
    )


def _recompute_existing_pages(section: OcrResultSection) -> list[int]:
    """Sets every section's existing_pages to the pages of its contents, and
    returns this section's."""
    pages: set[int] = set()

    for block in section.section_content:
        if isinstance(block, OcrResultSection):
            pages.update(_recompute_existing_pages(block))
        else:
            pages.update(block.existing_pages)

    section.existing_pages = sorted(pages)

    return section.existing_pages
