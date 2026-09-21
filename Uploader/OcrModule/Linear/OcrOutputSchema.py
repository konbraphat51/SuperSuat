from pydantic import BaseModel, Field

from ..OcrSchema import TEXT_BLOCK_TYPES


class AddTextBlockInputSchema(BaseModel):
    """Add a new text block to the specified section."""

    section_block_index: int = Field(
        description="The block_index of the section to add this block into."
    )
    block_type: TEXT_BLOCK_TYPES = Field(
        description="The kind of text block this is."
    )
    text: str = Field(description="The block's text.")


class AddImageBlockInputSchema(BaseModel):
    """Add a new figure block to the specified section. bounding_box must be
    in the pixel coordinates of the current page - use the clip_image tool to
    get an accurate one rather than estimating it by eye."""

    section_block_index: int = Field(
        description="The block_index of the section to add this block into."
    )
    bounding_box: tuple[int, int, int, int] = Field(
        description="(x, y, width, height) of the figure, in the current page's pixel coordinates."
    )
    caption: str = Field(description="The figure's caption.")


class AddSectionInputSchema(BaseModel):
    """Add a new empty section under the specified parent section."""

    parent_section_block_index: int = Field(
        description="The block_index of the section to add this new section into."
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
