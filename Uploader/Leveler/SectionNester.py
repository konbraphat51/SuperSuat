"""Flattening a document tree into its blocks, and nesting them again by heading level."""

from OcrModule.OcrSchema import OcrResultBlock, OcrResultSection

# The level the root section sits at, below every heading.
ROOT_HEADING_LEVEL = 0


def flatten_blocks(section: OcrResultSection) -> list[OcrResultBlock]:
    """Every block under the section that is not a section, in document order.

    Args:
        section: The section to flatten, usually a document's root section.
    """
    blocks: list[OcrResultBlock] = []

    for block in section.section_content:
        if isinstance(block, OcrResultSection):
            blocks += flatten_blocks(block)
        else:
            blocks.append(block)

    return blocks


def nest_by_levels(
    root_block_index: int,
    blocks: list[OcrResultBlock],
    heading_levels: dict[int, int],
) -> OcrResultSection:
    """The blocks as a tree, each heading opening a section nested by its level.

    A heading of the same level as the innermost open section starts a
    sibling, and one of a lower level closes every section it is not inside.
    The blocks are placed as they are, not copied; each new section gets a
    block_index above every index the blocks already use.

    Args:
        root_block_index: The block_index the root section is given.
        blocks: Every block of the document, in document order, none a section.
        heading_levels: The level of each heading, keyed by block_index. A
            block missing from it opens no section.
    """
    next_block_index = max([root_block_index, *(b.block_index for b in blocks)]) + 1

    root = _new_section(root_block_index)
    # the sections currently open, outermost first, as (heading level, section)
    open_sections: list[tuple[int, OcrResultSection]] = [(ROOT_HEADING_LEVEL, root)]

    for block in blocks:
        heading_level = heading_levels.get(block.block_index)

        # a heading opens the section its own content goes into
        if heading_level is not None:
            # the root is never closed
            while len(open_sections) > 1 and open_sections[-1][0] >= heading_level:
                open_sections.pop()

            section = _new_section(next_block_index)
            next_block_index += 1
            open_sections[-1][1].section_content.append(section)
            open_sections.append((heading_level, section))

        open_sections[-1][1].section_content.append(block)

    root.recompute_existing_pages()

    return root


def _new_section(block_index: int) -> OcrResultSection:
    """An empty section, its pages to be computed once it is filled."""
    return OcrResultSection(
        block_type="section",
        existing_pages=[],
        block_index=block_index,
        section_content=[],
    )
