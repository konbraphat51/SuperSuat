import logging

from ..OcrSchema import (
    OcrResultBlock,
    OcrResultBlockFigure,
    OcrResultBlockText,
    OcrResultSection,
)
from .OcrOutputSchema import (
    AddImageBlockOperation,
    AddSectionOperation,
    AddTextBlockOperation,
    EditBlockOperation,
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


def _section_exists(reference: str, entire_section: OcrResultSection) -> bool:
    """Whether `reference` names a section that already exists, by block_index."""
    try:
        find_section_by_index(int(reference), entire_section)
    except (ValueError, KeyError):
        return False

    return True


def validate_output(
    output: OutputSchema, entire_section: OcrResultSection
) -> list[str]:
    """Every problem that would stop `output` from being applied, phrased for
    the model that produced it - an empty list means it can be applied as is.

    Checked before anything is written, so a response with a bad reference in
    it can be handed back to the model whole, rather than half-applied and
    then rejected.

    The operations are checked in order, the same way they are applied: a
    temporary_id only counts as known once the add_section that declares it
    has been passed, which is what makes a forward reference (and so a cycle)
    impossible to express."""
    errors: list[str] = []
    known_ids: set[str] = set()

    for position, operation in enumerate(output.operations):
        where = f"operations[{position}] ({operation.operation})"

        if isinstance(operation, AddSectionOperation):
            temporary_id = operation.temporary_id.strip()

            if not temporary_id:
                errors.append(
                    f"{where}: temporary_id is empty. Give the section a short name."
                )
            elif temporary_id.lstrip("-").isdigit():
                errors.append(
                    f"{where}: temporary_id {temporary_id!r} is a number, which is ambiguous "
                    "with the block_index of a section that already exists. Use a name instead."
                )
            elif temporary_id in known_ids:
                errors.append(
                    f"{where}: temporary_id {temporary_id!r} is already used by an earlier "
                    "add_section. Each new section needs its own."
                )
            else:
                known_ids.add(temporary_id)

            parent = operation.parent.strip()
            if parent not in known_ids and not _section_exists(
                parent, entire_section
            ):
                errors.append(
                    f"{where}: parent {parent!r} is neither the block_index of an existing "
                    "section nor the temporary_id of a section added earlier in this list."
                )

        elif isinstance(
            operation, (AddTextBlockOperation, AddImageBlockOperation)
        ):
            section = operation.section.strip()
            if section not in known_ids and not _section_exists(
                section, entire_section
            ):
                errors.append(
                    f"{where}: section {section!r} is neither the block_index of an existing "
                    "section nor the temporary_id of a section added earlier in this list."
                )

        elif isinstance(operation, EditBlockOperation):
            try:
                block = find_block_by_index(
                    operation.block_index, entire_section
                )
            except KeyError:
                errors.append(
                    f"{where}: there is no block with block_index {operation.block_index}."
                )
                continue

            if not isinstance(block, OcrResultBlockText):
                errors.append(
                    f"{where}: block {operation.block_index} is a {block.block_type}, "
                    "not a text block, so its text cannot be edited."
                )

    return errors


class OcrDataEditor:
    """Applies one page's batched OutputSchema to the document tree.

    This is what replaced the sequential tool-calling loop: instead of one
    model round-trip per edit (each resending the whole conversation, page
    image included), the model reports every edit the page needs in a single
    OutputSchema, and this class performs them all at once - the same
    operations Tools.py's LinearTools used to perform one tool call at a
    time, minus the per-call "ERROR: ..." string replies, since there is no
    further model turn left in this page to read them.

    Expects `output` to have passed validate_output already - the caller
    hands a response back to the model rather than applying a broken one.
    The skip-and-warn paths below are only a backstop for that."""

    def __init__(self, entire_section: OcrResultSection) -> None:
        self.entire_section = entire_section

    def apply(self, output: OutputSchema, page_number: int) -> None:
        """Carries out `output.operations` in the order given.

        Order is the point: a block is appended to its section as its
        operation is reached, so the order the model reports them in is the
        order they end up in the document. Splitting them by kind first would
        put every figure after every paragraph, and every subsection before
        the heading that introduces it."""
        # temporary_id -> the block_index it actually got, so a later
        # operation can resolve a section that did not exist when it was named
        temporary_ids: dict[str, int] = {}

        for operation in output.operations:
            if isinstance(operation, AddSectionOperation):
                new_section_index = self._add_section(
                    operation, page_number, temporary_ids
                )
                if new_section_index is not None:
                    temporary_ids[operation.temporary_id.strip()] = (
                        new_section_index
                    )
            elif isinstance(operation, AddTextBlockOperation):
                self._add_text_block(operation, page_number, temporary_ids)
            elif isinstance(operation, AddImageBlockOperation):
                self._add_image_block(operation, page_number, temporary_ids)
            elif isinstance(operation, EditBlockOperation):
                self._edit_block(operation, page_number)

    def _resolve_section(
        self, reference: str, temporary_ids: dict[str, int]
    ) -> OcrResultSection | None:
        """The section a placement names, whether by the temporary_id of one
        added in this same response or by an existing block_index."""
        block_index = temporary_ids.get(reference.strip())

        if block_index is None:
            try:
                block_index = int(reference)
            except ValueError:
                return None

        try:
            return find_section_by_index(block_index, self.entire_section)
        except KeyError:
            return None

    def _add_section(
        self,
        operation: AddSectionOperation,
        page_number: int,
        temporary_ids: dict[str, int],
    ) -> int | None:
        parent_section = self._resolve_section(operation.parent, temporary_ids)
        if parent_section is None:
            logger.warning(
                "page %d | add_section: parent %r not found, skipping",
                page_number,
                operation.parent,
            )
            return None

        new_section_index = get_max_block_index(self.entire_section) + 1
        new_section = OcrResultSection(
            block_type="section",
            existing_pages=[],
            block_index=new_section_index,
            section_content=[],
        )
        parent_section.section_content.append(new_section)
        mark_existing_page(self.entire_section, new_section_index, page_number)

        return new_section_index

    def _edit_block(
        self, operation: EditBlockOperation, page_number: int
    ) -> None:
        try:
            block = find_block_by_index(operation.block_index, self.entire_section)
        except KeyError:
            logger.warning(
                "page %d | edit_block: block %d not found, skipping",
                page_number,
                operation.block_index,
            )
            return

        if not isinstance(block, OcrResultBlockText):
            logger.warning(
                "page %d | edit_block: block %d is not a text block, skipping",
                page_number,
                operation.block_index,
            )
            return

        block.text = operation.text
        mark_existing_page(self.entire_section, operation.block_index, page_number)

    def _add_text_block(
        self,
        operation: AddTextBlockOperation,
        page_number: int,
        temporary_ids: dict[str, int],
    ) -> None:
        section = self._resolve_section(operation.section, temporary_ids)
        if section is None:
            logger.warning(
                "page %d | add_text_block: section %r not found, skipping",
                page_number,
                operation.section,
            )
            return

        new_block_index = get_max_block_index(self.entire_section) + 1
        new_block = OcrResultBlockText(
            block_type=operation.block_type,
            existing_pages=[],
            block_index=new_block_index,
            text=operation.text,
        )
        section.section_content.append(new_block)
        mark_existing_page(self.entire_section, new_block_index, page_number)

    def _add_image_block(
        self,
        operation: AddImageBlockOperation,
        page_number: int,
        temporary_ids: dict[str, int],
    ) -> None:
        section = self._resolve_section(operation.section, temporary_ids)
        if section is None:
            logger.warning(
                "page %d | add_image_block: section %r not found, skipping",
                page_number,
                operation.section,
            )
            return

        new_block_index = get_max_block_index(self.entire_section) + 1
        new_block = OcrResultBlockFigure(
            block_type="figure",
            existing_pages=[],
            block_index=new_block_index,
            page_number=page_number,
            bounding_box=operation.bounding_box,
            caption=operation.caption,
        )
        section.section_content.append(new_block)
        mark_existing_page(self.entire_section, new_block_index, page_number)
