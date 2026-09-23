# The edits an OrganizerAgent may request on the blocks being organized.

from pydantic import BaseModel, Field
from typing import Annotated, Literal
from ...OcrSchema import TEXT_BLOCK_TYPES

ORDER_LABELS = Literal[
    "set_block_type",
    "set_heading_level",
    "reorder",
    "delete_block",
    "edit_block",
    "set_caption",
    "merge_blocks",
]


class Order(BaseModel):
    """One edit to apply to the blocks being organized.

    Attributes:
        order_label: Which edit this is; each subclass fixes it to its own value.
    """

    order_label: ORDER_LABELS


class OrderSetBlockType(Order):
    """Labels a text block with the type it turned out to be."""

    order_label: Literal["set_block_type"] = "set_block_type"
    target_block_id: int = Field(
        description="The block_index of the block to set the label for."
    )
    new_label: TEXT_BLOCK_TYPES = Field(
        description="The new block_type to set for the block."
    )


class OrderSetHeadingLevel(Order):
    """Places a heading in the document's heading hierarchy."""

    order_label: Literal["set_heading_level"] = "set_heading_level"
    target_block_id: int = Field(
        description="The block_index of the block to set the heading level for."
    )
    new_level: int = Field(description="The new heading level to set for the block.")


class OrderReorder(Order):
    """Moves a block to its place in the document's reading order."""

    order_label: Literal["reorder"] = "reorder"
    target_block_id: int = Field(description="The block_index of the block to reorder.")
    to_in_front_of_block_id: int = Field(
        description="The block_index of the block to place the target block in front of."
    )


class OrderDeleteBlock(Order):
    """Drops a block that does not belong in the document."""

    order_label: Literal["delete_block"] = "delete_block"
    target_block_id: int = Field(description="The block_index of the block to delete.")


class OrderEditBlock(Order):
    """Corrects a text block, changing only the fields that are filled in."""

    order_label: Literal["edit_block"] = "edit_block"
    target_block_id: int = Field(description="The block_index of the block to edit.")
    new_label: TEXT_BLOCK_TYPES | None = Field(
        description="The new block_type to set for the block, if changing."
    )
    new_text: str | None = Field(
        description="The new text to set for the block, if changing."
    )
    new_heading_level: int | None = Field(
        description="The new heading level to set for the block, if changing."
    )


class OrderMergeBlocks(Order):
    """Joins a text block split in two back into one block."""

    order_label: Literal["merge_blocks"] = "merge_blocks"
    former_block_id: int = Field(
        description="The block_index of the block whose text comes first. The merged text is kept on this block."
    )
    latter_block_id: int = Field(
        description="The block_index of the block whose text follows, which is appended to the former block and then removed."
    )
    join_with_space: bool = Field(
        description="True to put a space between the two texts, as a language that separates words with spaces (English etc.) needs. False to join them directly, as Japanese, Chinese and the like need."
    )


class OrderSetCaption(Order):
    """Records the caption of a figure, or that it has none."""

    order_label: Literal["set_caption"] = "set_caption"
    target_image_block_id: int = Field(
        description="The block_index of the image block to set the caption for."
    )
    target_caption_block_id: int | None = Field(
        description="The block_index of the text block to set as the caption for the image block, or null if the figure has no caption printed with it."
    )


# order_label tells the model's JSON which order it is sending, and tells
# pydantic which schema to validate it against
AnyOrder = Annotated[
    OrderSetBlockType
    | OrderSetHeadingLevel
    | OrderReorder
    | OrderDeleteBlock
    | OrderEditBlock
    | OrderSetCaption
    | OrderMergeBlocks,
    Field(discriminator="order_label"),
]


class OrderBatch(BaseModel):
    """One round of edits from the organizer model.

    Attributes:
        orders: The edits to apply, in the order they are listed.
        is_last_batch: Whether the page is finished after this batch.
    """

    orders: list[AnyOrder] = Field(
        description="The list of orders to apply, in order. Each order is applied to the document state resulting from all previous orders in this list."
    )
    is_last_batch: bool = Field(
        description="True if this page needs no further orders after this batch, false if you want to see the result and continue working on this page."
    )
