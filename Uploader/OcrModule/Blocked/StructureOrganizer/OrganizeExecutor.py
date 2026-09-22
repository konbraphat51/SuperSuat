# Applies the orders an OrganizerAgent issues to the blocks being organized.

from dataclasses import fields
from .OrderSchema import (
    Order,
    OrderBatch,
    OrderSetBlockType,
    OrderSetHeadingLevel,
    OrderReorder,
    OrderDeleteBlock,
    OrderEditBlock,
    OrderSetCaption,
)
from .ProcessingSchema import (
    ProcessingBlock,
    ProcessingBlockText,
    ProcessingBlockTextHeading,
    ProcessingBlockFigure,
)


def execute_orders(
    order_batch: OrderBatch,
    processing_data: list[ProcessingBlock],
) -> None:
    """Applies every order of order_batch to processing_data, in list order.

    processing_data is mutated in place: each order sees the state left by all
    previous orders of the batch.

    Args:
        order_batch: The orders to apply, in the order they are listed.
        processing_data: The blocks being organized, in document order.

    Raises:
        ValueError: An order targets a block_id absent from processing_data,
            or targets a block of a kind the order cannot be applied to.
        TypeError: An order's payload does not match its order_label.
    """
    # for each order...
    for order in order_batch.orders:
        _execute_order(order, processing_data)


def _execute_order(order: Order, processing_data: list[ProcessingBlock]) -> None:
    """Applies a single order to processing_data."""
    match order.order_label:
        case "set_block_type":
            _execute_set_block_type(_as(order, OrderSetBlockType), processing_data)
        case "set_heading_level":
            _execute_set_heading_level(_as(order, OrderSetHeadingLevel), processing_data)
        case "reorder":
            _execute_reorder(_as(order, OrderReorder), processing_data)
        case "delete_block":
            _execute_delete_block(_as(order, OrderDeleteBlock), processing_data)
        case "edit_block":
            _execute_edit_block(_as(order, OrderEditBlock), processing_data)
        case "set_caption":
            _execute_set_caption(_as(order, OrderSetCaption), processing_data)
        case _:
            raise ValueError(f"Unknown order label: {order.order_label}")


def _execute_set_block_type(
    order: OrderSetBlockType, processing_data: list[ProcessingBlock]
) -> None:
    """Labels the target block with the given text block type."""
    index = _find_index(processing_data, order.target_block_id)
    block = _require_text(processing_data[index], order.target_block_id)

    # a heading needs the richer block so a level can be attached later
    if order.new_label == "heading":
        block = _promote_to_heading(block)
        processing_data[index] = block

    block.new_type = order.new_label
    block.have_been_labeled = True


def _execute_set_heading_level(
    order: OrderSetHeadingLevel, processing_data: list[ProcessingBlock]
) -> None:
    """Sets the heading level of the target block, making it a heading."""
    index = _find_index(processing_data, order.target_block_id)
    block = _promote_to_heading(
        _require_text(processing_data[index], order.target_block_id)
    )
    processing_data[index] = block

    block.new_type = "heading"
    block.have_been_labeled = True
    block.heading_level = order.new_level


def _execute_reorder(
    order: OrderReorder, processing_data: list[ProcessingBlock]
) -> None:
    """Moves the target block immediately in front of the anchor block."""
    if order.target_block_id == order.to_in_front_of_block_id:
        return

    target_index = _find_index(processing_data, order.target_block_id)
    # look the anchor up before the move, so a missing one leaves the list untouched
    _find_index(processing_data, order.to_in_front_of_block_id)

    block = processing_data.pop(target_index)
    processing_data.insert(
        _find_index(processing_data, order.to_in_front_of_block_id), block
    )


def _execute_delete_block(
    order: OrderDeleteBlock, processing_data: list[ProcessingBlock]
) -> None:
    """Removes the target block, dropping captions pointing at it."""
    index = _find_index(processing_data, order.target_block_id)
    processing_data.pop(index)

    # keep figures from referencing a block that is gone
    for block in processing_data:
        if (
            isinstance(block, ProcessingBlockFigure)
            and block.caption_text_block_id == order.target_block_id
        ):
            block.caption_text_block_id = None
            block.have_caption_set = False


def _execute_edit_block(
    order: OrderEditBlock, processing_data: list[ProcessingBlock]
) -> None:
    """Applies every field the order fills in to the target text block."""
    index = _find_index(processing_data, order.target_block_id)
    block = _require_text(processing_data[index], order.target_block_id)

    # a level, or a "heading" label, needs the richer block
    if order.new_heading_level is not None or order.new_label == "heading":
        block = _promote_to_heading(block)
        processing_data[index] = block

    if order.new_label is not None:
        block.new_type = order.new_label
        block.have_been_labeled = True

    if order.new_text is not None:
        block.text = order.new_text
        block.have_been_edited = True

    if order.new_heading_level is not None:
        assert isinstance(block, ProcessingBlockTextHeading)
        block.heading_level = order.new_heading_level


def _execute_set_caption(
    order: OrderSetCaption, processing_data: list[ProcessingBlock]
) -> None:
    """Assigns a text block as the caption of a figure block."""
    figure = processing_data[_find_index(processing_data, order.target_image_block_id)]
    if not isinstance(figure, ProcessingBlockFigure):
        raise ValueError(
            f"Block {order.target_image_block_id} is not a figure block, "
            "so it cannot take a caption."
        )

    _require_text(
        processing_data[_find_index(processing_data, order.target_caption_block_id)],
        order.target_caption_block_id,
    )

    figure.caption_text_block_id = order.target_caption_block_id
    figure.have_caption_set = True


def _find_index(processing_data: list[ProcessingBlock], block_id: int) -> int:
    """Returns the position of the block with block_id, in processing_data."""
    for index, block in enumerate(processing_data):
        if block.block_id == block_id:
            return index

    raise ValueError(f"No block with block_id {block_id} in processing_data.")


def _require_text(block: ProcessingBlock, block_id: int) -> ProcessingBlockText:
    """Returns block as a text block, rejecting any other kind."""
    if not isinstance(block, ProcessingBlockText):
        raise ValueError(f"Block {block_id} is not a text block.")

    return block


def _promote_to_heading(block: ProcessingBlockText) -> ProcessingBlockTextHeading:
    """Returns block as a heading block, reusing it if it already is one."""
    if isinstance(block, ProcessingBlockTextHeading):
        return block

    return ProcessingBlockTextHeading(
        **{field.name: getattr(block, field.name) for field in fields(block)}
    )


def _as[T: Order](order: Order, order_type: type[T]) -> T:
    """Returns order narrowed to the schema its order_label promises."""
    if not isinstance(order, order_type):
        raise TypeError(
            f"Order labeled {order.order_label} is not a {order_type.__name__}."
        )

    return order
