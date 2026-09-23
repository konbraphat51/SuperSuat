# The edits a Classifier may request on the blocks being organized.

from pydantic import BaseModel, Field
from typing import Annotated, Literal
from ....OcrSchema import TEXT_BLOCK_TYPES

ORDER_LABELS = Literal[
    "set_block_type",
    "reorder",
    "delete_block",
    "edit_block",
    "set_caption",
    "set_merging_previous_page",
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


class OrderSetMergingPreviousPage(Order):
    """Marks a block as the rest of a block the previous page broke off."""

    order_label: Literal["set_merging_previous_page"] = "set_merging_previous_page"
    target_block_id: int = Field(
        description="The block_index of the block that continues from the previous page."
    )
    merging_previous_page: bool = Field(
        description="True if this block is the rest of a block the previous page broke off in the middle, so the two are written down as one. False to take that mark back."
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
    | OrderReorder
    | OrderDeleteBlock
    | OrderEditBlock
    | OrderSetCaption
    | OrderSetMergingPreviousPage,
    Field(discriminator="order_label"),
]


class OrderBatch(BaseModel):
    """One round of edits from the classifier model.

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
