from typing import Literal

from pydantic import BaseModel, Field

from ..OcrSchema import TEXT_BLOCK_TYPES

SECTION_REFERENCE_DESCRIPTION = (
    "Which section to put this into: the block_index of a section that already "
    'exists, written as a string (e.g. "0"), or the temporary_id of a section '
    "added by an add_section operation EARLIER in this same list."
)


class AddSectionOperation(BaseModel):
    """Add a new empty section, which later operations in this same list can
    then put blocks into by naming its temporary_id."""

    operation: Literal["add_section"]
    temporary_id: str = Field(
        description=(
            "A short name you choose for this new section, so later operations can "
            'put blocks into it (e.g. "chapter-2"). It must be unique within this '
            "list, and must not be a number - a number would be ambiguous with the "
            "block_index of a section that already exists."
        )
    )
    parent: str = Field(
        description=(
            "Which section to put this new section into: the block_index of a section "
            'that already exists, written as a string (e.g. "0"), or the temporary_id '
            "of a section added EARLIER in this same list."
        )
    )


class AddTextBlockOperation(BaseModel):
    """Add a new text block to a section."""

    operation: Literal["add_text_block"]
    section: str = Field(description=SECTION_REFERENCE_DESCRIPTION)
    block_type: TEXT_BLOCK_TYPES = Field(
        description="The kind of text block this is."
    )
    text: str = Field(description="The block's text.")


class AddImageBlockOperation(BaseModel):
    """Add a new figure block to a section. bounding_box must be in the pixel
    coordinates of the current page - use the clip_image tool to get an
    accurate one rather than estimating it by eye."""

    operation: Literal["add_image_block"]
    section: str = Field(description=SECTION_REFERENCE_DESCRIPTION)
    # Four separate fields rather than one (x, y, width, height) tuple:
    # a fixed-length tuple becomes a prefixItems array in the JSON schema,
    # which structured output rejects ("array schema missing items").
    x: int = Field(
        description="Left edge of the figure, in the current page's pixel coordinates."
    )
    y: int = Field(
        description="Top edge of the figure, in the current page's pixel coordinates."
    )
    width: int = Field(description="Width of the figure, in pixels.")
    height: int = Field(description="Height of the figure, in pixels.")
    caption: str = Field(description="The figure's caption.")

    @property
    def bounding_box(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.width, self.height)


class EditBlockOperation(BaseModel):
    """Edit the text of a block that already exists, by its block_index."""

    operation: Literal["edit_block"]
    block_index: int = Field(
        description="The block_index of the block to edit. It must already exist - a block added by this same list has no block_index yet."
    )
    text: str = Field(description="The block's new text.")


Operation = (
    AddSectionOperation
    | AddTextBlockOperation
    | AddImageBlockOperation
    | EditBlockOperation
)


class OutputSchema(BaseModel):
    """Everything to do to the document for the current page, as one list in
    the order it should be carried out.

    A single ordered list rather than one list per kind of operation: blocks
    are appended to their section as they are applied, so the order here is
    the order they end up in the document. Report them in the order they read
    on the page."""

    operations: list[Operation] = []
