from pydantic import BaseModel, Field
from typing import Literal
from ...OcrSchema import TEXT_BLOCK_TYPES


class Order(BaseModel):
    order_label: Literal[
        "set_block_type",
        "set_heading_level",
        "reorder",
        "delete_block",
        "edit_block",
        "set_caption",
    ]


class OrderSetBlockType(Order):
    target_block_id: int = Field(
        description="The block_index of the block to set the label for."
    )
    new_label: TEXT_BLOCK_TYPES = Field(
        description="The new block_type to set for the block."
    )


class OrderSetHeadingLevel(Order):
    target_block_id: int = Field(
        description="The block_index of the block to set the heading level for."
    )
    new_level: int = Field(description="The new heading level to set for the block.")


class OrderReorder(Order):
    target_block_id: int = Field(description="The block_index of the block to reorder.")
    to_in_front_of_block_id: int = Field(
        description="The block_index of the block to place the target block in front of."
    )


class OrderDeleteBlock(Order):
    target_block_id: int = Field(description="The block_index of the block to delete.")


class OrderEditBlock(Order):
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


class OrderSetCaption(Order):
    target_image_block_id: int = Field(
        description="The block_index of the image block to set the caption for."
    )
    target_caption_block_id: int = Field(
        description="The block_index of the text block to set as the caption for the image block."
    )


class OrderBatch(BaseModel):
    orders: list[Order] = Field(
        description="The list of orders to apply, in order. Each order is applied to the document state resulting from all previous orders in this list."
    )
    is_last_batch: bool = Field(
        description="Whether this is the last batch of orders for the page. If True, you cannot order further edits."
    )
