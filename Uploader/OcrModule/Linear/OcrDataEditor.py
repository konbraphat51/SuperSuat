import logging

from ..OcrSchema import (
    OcrResultBlock,
    OcrResultBlockFigure,
    OcrResultBlockText,
    OcrResultSection,
)
from .OcrOutputSchema import (
    AddImageBlockInputSchema,
    AddSectionInputSchema,
    AddTextBlockInputSchema,
    EditBlockInputSchema,
    OutputSchema,
)

logger = logging.getLogger(__name__)


def find_block_by_index(
    index: int,
    section: OcrResultSection,
) -> OcrResultBlock:
    if section.block_index == index:
        return section

    for block in section.section_content:
        if block.block_index == index:
            return block

        if isinstance(block, OcrResultSection):
            try:
                return find_block_by_index(index, block)
            except KeyError:
                continue

    raise KeyError(f"Block with index {index} not found")


def find_section_by_index(
    index: int,
    section: OcrResultSection,
) -> OcrResultSection:
    if section.block_index == index:
        return section

    for block in section.section_content:
        if isinstance(block, OcrResultSection):
            try:
                return find_section_by_index(index, block)
            except KeyError:
                continue

    raise KeyError(f"Section with index {index} not found")


def get_max_block_index(section: OcrResultSection) -> int:
    max_index = section.block_index

    for block in section.section_content:
        if block.block_index > max_index:
            max_index = block.block_index

        if isinstance(block, OcrResultSection):
            child_max_index = get_max_block_index(block)
            if child_max_index > max_index:
                max_index = child_max_index

    return max_index


def mark_existing_page(
    entire_section: OcrResultSection,
    target_index: int,
    page_number: int,
) -> bool:
    """Adds page_number to existing_pages of the block with target_index and every ancestor section, including `section` itself. Returns whether target_index was found within `section`."""
    if entire_section.block_index == target_index:
        if page_number not in entire_section.existing_pages:
            entire_section.existing_pages.append(page_number)
        return True

    found = False
    for block in entire_section.section_content:
        if block.block_index == target_index:
            if page_number not in block.existing_pages:
                block.existing_pages.append(page_number)
            found = True
            break

        if isinstance(block, OcrResultSection) and mark_existing_page(
            block, target_index, page_number
        ):
            found = True
            break

    if found and page_number not in entire_section.existing_pages:
        entire_section.existing_pages.append(page_number)

    return found


class OcrDataEditor:
    """Applies one page's batched OutputSchema to the document tree.

    This is what replaced the sequential tool-calling loop: instead of one
    model round-trip per edit (each resending the whole conversation, page
    image included), the model reports every edit the page needs in a single
    OutputSchema, and this class performs them all at once - the same
    operations Tools.py's LinearTools used to perform one tool call at a
    time, minus the per-call "ERROR: ..." string replies, since there is no
    further model turn left in this page to read them. An operation that
    targets a section or block that doesn't exist is logged and skipped
    instead, so one bad reference costs only itself rather than the page."""

    def __init__(self, entire_section: OcrResultSection) -> None:
        self.entire_section = entire_section

    def apply(self, output: OutputSchema, page_number: int) -> None:
        """Applies every edit in `output`, in a fixed order: new sections
        first, then edits to existing blocks, then new text and figure
        blocks. Note that a section added here has no block_index the model
        could have known about when it wrote this same response, so
        section_block_index on an addition below always has to name a
        section that already existed before this page - never one from
        `output.adding_section` itself."""
        for addition in output.adding_section:
            self._add_section(addition, page_number)

        for edit in output.editing_block:
            self._edit_block(edit, page_number)

        for addition in output.adding_text_block:
            self._add_text_block(addition, page_number)

        for addition in output.adding_image_block:
            self._add_image_block(addition, page_number)

    def _add_section(
        self, addition: AddSectionInputSchema, page_number: int
    ) -> None:
        try:
            parent_section = find_section_by_index(
                addition.parent_section_block_index, self.entire_section
            )
        except KeyError:
            logger.warning(
                "page %d | add_section: section %d not found, skipping",
                page_number,
                addition.parent_section_block_index,
            )
            return

        new_section_index = get_max_block_index(self.entire_section) + 1
        new_section = OcrResultSection(
            block_type="section",
            existing_pages=[],
            block_index=new_section_index,
            section_content=[],
        )
        parent_section.section_content.append(new_section)
        mark_existing_page(self.entire_section, new_section_index, page_number)

    def _edit_block(
        self, edit: EditBlockInputSchema, page_number: int
    ) -> None:
        try:
            block = find_block_by_index(edit.block_index, self.entire_section)
        except KeyError:
            logger.warning(
                "page %d | edit_block: block %d not found, skipping",
                page_number,
                edit.block_index,
            )
            return

        if not isinstance(block, OcrResultBlockText):
            logger.warning(
                "page %d | edit_block: block %d is not a text block, skipping",
                page_number,
                edit.block_index,
            )
            return

        block.text = edit.text
        mark_existing_page(self.entire_section, edit.block_index, page_number)

    def _add_text_block(
        self, addition: AddTextBlockInputSchema, page_number: int
    ) -> None:
        try:
            section = find_section_by_index(
                addition.section_block_index, self.entire_section
            )
        except KeyError:
            logger.warning(
                "page %d | add_text_block: section %d not found, skipping",
                page_number,
                addition.section_block_index,
            )
            return

        new_block_index = get_max_block_index(self.entire_section) + 1
        new_block = OcrResultBlockText(
            block_type=addition.block_type,
            existing_pages=[],
            block_index=new_block_index,
            text=addition.text,
        )
        section.section_content.append(new_block)
        mark_existing_page(self.entire_section, new_block_index, page_number)

    def _add_image_block(
        self, addition: AddImageBlockInputSchema, page_number: int
    ) -> None:
        try:
            section = find_section_by_index(
                addition.section_block_index, self.entire_section
            )
        except KeyError:
            logger.warning(
                "page %d | add_image_block: section %d not found, skipping",
                page_number,
                addition.section_block_index,
            )
            return

        new_block_index = get_max_block_index(self.entire_section) + 1
        new_block = OcrResultBlockFigure(
            block_type="figure",
            existing_pages=[],
            block_index=new_block_index,
            page_number=page_number,
            bounding_box=addition.bounding_box,
            caption=addition.caption,
        )
        section.section_content.append(new_block)
        mark_existing_page(self.entire_section, new_block_index, page_number)
