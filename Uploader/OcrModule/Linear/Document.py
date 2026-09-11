from typing import Any

from ..OcrSchema import (
    OcrResultBlock,
    OcrResultBlockImage,
    OcrResultBlockText,
    OcrResultSection,
)
from .Xml import ROOT_SECTION_ID, child_section_id, section_to_xml

EDITABLE_FIELDS = ("text", "text_type", "caption", "existing_pages")


class LinearDocument:
    """The document the OCR agent is building, and the way it addresses it."""

    def __init__(self) -> None:
        self.root = OcrResultSection(
            section_content=[],
            child_sections=[]
        )
        # block indexes are given by the program, never by the agent
        self.next_block_index = 0

    def to_xml(self) -> str:
        return section_to_xml(self.root, ROOT_SECTION_ID)

    def add_text_block(
        self,
        section_id: str,
        existing_pages: list[int],
        text: str,
        text_type: str,
    ) -> int:
        """Append a text block to the section. Returns the index given to it."""
        return self._append(
            section_id,
            lambda block_index: OcrResultBlockText(
                block_type="text",
                existing_pages=existing_pages,
                block_index=block_index,
                text=text,
                text_type=text_type,
            ),
        )

    def add_image_block(
        self,
        section_id: str,
        existing_pages: list[int],
        image_data: bytes,
        caption: str,
    ) -> int:
        """Append an image block to the section. Returns the index given to it."""
        return self._append(
            section_id,
            lambda block_index: OcrResultBlockImage(
                block_type="image",
                existing_pages=existing_pages,
                block_index=block_index,
                image_data=image_data,
                caption=caption,
            ),
        )

    def edit_block(
        self,
        block_index: int,
        updates: dict[str, Any],
    ) -> list[str]:
        """Overwrite the given fields of the block. Returns the edited field names."""
        block = self.find_block(block_index)
        if block is None:
            raise ValueError(f"no block has the index {block_index}.")

        edited = []
        for field in EDITABLE_FIELDS:
            if field not in updates:
                continue
            if not hasattr(block, field):
                raise ValueError(
                    f"the block {block_index} is a {block.block_type} block "
                    f"and has no `{field}`."
                )
            setattr(block, field, updates[field])
            edited.append(field)

        if not edited:
            raise ValueError("nothing to edit: give at least one field to overwrite.")

        return edited

    def find_section(
        self,
        section_id: str,
        section: OcrResultSection | None = None,
        current_id: str = ROOT_SECTION_ID,
    ) -> OcrResultSection | None:
        section = self.root if section is None else section

        if section_id == current_id:
            return section

        for index, child in enumerate(section.child_sections):
            found = self.find_section(
                section_id, child, child_section_id(current_id, index)
            )
            if found is not None:
                return found

        return None

    def find_block(
        self,
        block_index: int,
        section: OcrResultSection | None = None,
    ) -> OcrResultBlock | None:
        section = self.root if section is None else section

        for block in section.section_content:
            if block.block_index == block_index:
                return block

        for child in section.child_sections:
            found = self.find_block(block_index, child)
            if found is not None:
                return found

        return None

    def all_blocks(
        self,
        section: OcrResultSection | None = None,
    ) -> list[OcrResultBlock]:
        """Every block of the document, in reading order."""
        section = self.root if section is None else section

        blocks = list(section.section_content)
        for child in section.child_sections:
            blocks.extend(self.all_blocks(child))

        return blocks

    def _append(self, section_id: str, build_block) -> int:
        section = self.find_section(section_id)
        if section is None:
            raise ValueError(f"no section has the id {section_id}.")

        block_index = self.next_block_index
        section.section_content.append(build_block(block_index))
        self.next_block_index += 1

        return block_index
