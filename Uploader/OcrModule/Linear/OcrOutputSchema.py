from pydantic import BaseModel, Field

from ..OcrSchema import TEXT_BLOCK_TYPES

SECTION_REFERENCE_DESCRIPTION = (
    "Which section to put this into: the block_index of a section that already "
    'exists, written as a string (e.g. "0"), or the temporary_id of a section '
    "from adding_section in this same response."
)


class AddTextBlockInputSchema(BaseModel):
    """Add a new text block to the specified section."""

    section: str = Field(description=SECTION_REFERENCE_DESCRIPTION)
    block_type: TEXT_BLOCK_TYPES = Field(
        description="The kind of text block this is."
    )
    text: str = Field(description="The block's text.")


class AddImageBlockInputSchema(BaseModel):
    """Add a new figure block to the specified section. bounding_box must be
    in the pixel coordinates of the current page - use the clip_image tool to
    get an accurate one rather than estimating it by eye."""

    section: str = Field(description=SECTION_REFERENCE_DESCRIPTION)
    bounding_box: tuple[int, int, int, int] = Field(
        description="(x, y, width, height) of the figure, in the current page's pixel coordinates."
    )
    caption: str = Field(description="The figure's caption.")


class AddSectionInputSchema(BaseModel):
    """Add a new empty section, which blocks in this same response can then be
    placed into by naming its temporary_id."""

    temporary_id: str = Field(
        description=(
            "A short name you choose for this new section, so blocks in this same "
            'response can be placed into it (e.g. "chapter-2"). It must be unique '
            "within this response, and must not be a number - a number would be "
            "ambiguous with the block_index of a section that already exists."
        )
    )
    parent: str = Field(
        description=(
            "Which section to put this new section into: the block_index of a section "
            'that already exists, written as a string (e.g. "0"), or the temporary_id '
            "of another section listed BEFORE this one in adding_section."
        )
    )


class EditBlockInputSchema(BaseModel):
    """Edit the text of an existing block by its index."""

    block_index: int = Field(
        description="The block_index of the block to edit."
    )
    text: str = Field(description="The block's new text.")


class OutputSchema(BaseModel):
    adding_text_block: list[AddTextBlockInputSchema] = []
    adding_image_block: list[AddImageBlockInputSchema] = []
    adding_section: list[AddSectionInputSchema] = []
    editing_block: list[EditBlockInputSchema] = []
