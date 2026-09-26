"""Tests for a document tree being flattened and nested again by heading level."""

from OcrModule.Blocked.StructureOrganizer.Leveler.SectionNester import (
    flatten_blocks,
    nest_by_levels,
)
from OcrModule.OcrSchema import OcrResultBlock, OcrResultBlockText, OcrResultSection


def text(block_index: int, block_type: str = "paragraph", page: int = 0):
    return OcrResultBlockText(
        block_type=block_type,  # type: ignore[arg-type]
        existing_pages=[page],
        block_index=block_index,
        text=f"block {block_index}",
    )


def section(block_index: int, *content: OcrResultBlock) -> OcrResultSection:
    return OcrResultSection(
        block_type="section",
        existing_pages=[],
        block_index=block_index,
        section_content=list(content),
    )


def shape(tree: OcrResultSection) -> list:
    """The tree as nested lists of the block indices of its non-section blocks."""
    return [
        shape(block) if isinstance(block, OcrResultSection) else block.block_index
        for block in tree.section_content
    ]


def test_flattening_drops_every_section_and_keeps_document_order():
    tree = section(0, text(1), section(2, text(3, "heading"), section(4, text(5))))

    assert [b.block_index for b in flatten_blocks(tree)] == [1, 3, 5]


def test_headings_nest_by_level_and_a_lower_level_closes_the_deeper_sections():
    blocks = [
        text(1),
        text(2, "heading"),
        text(3),
        text(4, "heading"),
        text(5),
        text(6, "heading"),
        text(7),
    ]

    root = nest_by_levels(0, blocks, {2: 1, 4: 2, 6: 1})

    assert shape(root) == [1, [2, 3, [4, 5]], [6, 7]]


def test_a_heading_of_the_same_level_starts_a_sibling():
    blocks = [text(1, "heading"), text(2, "heading"), text(3)]

    root = nest_by_levels(0, blocks, {1: 2, 2: 2})

    assert shape(root) == [[1], [2, 3]]


def test_a_heading_without_a_level_opens_no_section():
    blocks = [text(1, "heading"), text(2, "heading"), text(3)]

    root = nest_by_levels(0, blocks, {1: 1})

    assert shape(root) == [[1, 2, 3]]


def test_new_sections_take_indices_above_every_block_and_pages_are_recomputed():
    blocks = [text(10, "heading", page=2), text(11, page=3)]

    root = nest_by_levels(0, blocks, {10: 1})

    opened = root.section_content[0]
    assert isinstance(opened, OcrResultSection)
    assert opened.block_index == 12
    assert opened.existing_pages == [2, 3]
    assert root.existing_pages == [2, 3]
