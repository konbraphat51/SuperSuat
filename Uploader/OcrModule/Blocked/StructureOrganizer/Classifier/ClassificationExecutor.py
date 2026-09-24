# Applies the orders a Classifier issues to the blocks being organized.

from .OrderSchema import (
    Order,
    OrderBatch,
    OrderDeleteBlock,
    OrderReorder,
    OrderSetBlockType,
    OrderSetCaption,
    OrderSetMergingPreviousPage,
)
from ..ProcessingSchema import (
    FIGURE_LABEL,
    HEADING_LABEL,
    BLOCK_LABELS,
    ProcessingBlock,
    ProcessingBlockFigure,
    ProcessingBlockText,
    ProcessingBlockTextHeading,
    rebuild_block_as,
)

# What a block turns into when it is labeled. Everything else is a text block:
# the label says what kind of text, which the block itself does not care about.
LABEL_BLOCK_KINDS: dict[str, type[ProcessingBlock]] = {
    FIGURE_LABEL: ProcessingBlockFigure,
    HEADING_LABEL: ProcessingBlockTextHeading,
}


def execute_orders(
    order_batch: OrderBatch,
    processing_data: list[ProcessingBlock],
) -> None:
    """Applies every order of order_batch to processing_data, in list order.

    processing_data is mutated in place: each order sees the state left by all
    previous orders of the batch.

    Args:
        order_batch: The orders to apply, in the order they are listed.
        processing_data: The blocks of the page being classified, in reading
            order. An order reaches these and no other block of the document.

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
        case "reorder":
            _execute_reorder(_as(order, OrderReorder), processing_data)
        case "delete_block":
            _execute_delete_block(_as(order, OrderDeleteBlock), processing_data)
        case "set_caption":
            _execute_set_caption(_as(order, OrderSetCaption), processing_data)
        case "set_merging_previous_page":
            _execute_set_merging_previous_page(
                _as(order, OrderSetMergingPreviousPage), processing_data
            )
        case _:
            raise ValueError(f"Unknown order label: {order.order_label}")


def _execute_set_block_type(
    order: OrderSetBlockType, processing_data: list[ProcessingBlock]
) -> None:
    """Labels the target block, turning it into the kind of block it now is."""
    index = _find_index(processing_data, order.target_block_id)

    block = _labeled_block_kind(processing_data[index], order.new_label)
    block.new_type = order.new_label
    block.have_been_labeled = True
    processing_data[index] = block


def _labeled_block_kind(
    block: ProcessingBlock, new_label: BLOCK_LABELS
) -> ProcessingBlock:
    """The block as the kind its new label calls for.

    A label is also a change of kind: a heading carries a level, a figure
    carries a caption and no text of its own, and a block that stops being
    either goes back to a plain text block rather than keeping what it was
    given as something it no longer is.
    """
    return rebuild_block_as(
        block, LABEL_BLOCK_KINDS.get(new_label, ProcessingBlockText)
    )


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
    _remove_block(processing_data, order.target_block_id)


def _execute_set_caption(
    order: OrderSetCaption, processing_data: list[ProcessingBlock]
) -> None:
    """Assigns a text block as the caption of a figure block, or records that
    the figure has none when target_caption_block_id is None."""
    figure = processing_data[_find_index(processing_data, order.target_image_block_id)]
    if not isinstance(figure, ProcessingBlockFigure):
        raise ValueError(
            f"Block {order.target_image_block_id} is not a figure block, "
            "so it cannot take a caption."
        )

    if order.target_caption_block_id is not None:
        _require_text(
            processing_data[
                _find_index(processing_data, order.target_caption_block_id)
            ],
            order.target_caption_block_id,
        )

    figure.caption_text_block_id = order.target_caption_block_id
    # the figure is checked either way: having no caption is an answer too
    figure.have_caption_checked = True


def _execute_set_merging_previous_page(
    order: OrderSetMergingPreviousPage, processing_data: list[ProcessingBlock]
) -> None:
    """Marks the target block as continuing a block of the previous page."""
    block = _require_text(
        processing_data[_find_index(processing_data, order.target_block_id)],
        order.target_block_id,
    )

    if order.merging_previous_page and block.page_index == 0:
        raise ValueError(
            f"Block {order.target_block_id} is on the first page, "
            "so there is no previous page for it to continue from."
        )

    block.merging_previous_page = order.merging_previous_page


def _remove_block(processing_data: list[ProcessingBlock], block_id: int) -> None:
    """Drops the block from the document, and any caption pointing at it."""
    processing_data.pop(_find_index(processing_data, block_id))

    # keep figures from referencing a block that is gone
    for block in processing_data:
        if (
            isinstance(block, ProcessingBlockFigure)
            and block.caption_text_block_id == block_id
        ):
            block.caption_text_block_id = None
            block.have_caption_checked = False


def _find_index(processing_data: list[ProcessingBlock], block_id: int) -> int:
    """Returns the position of the block with block_id, in processing_data."""
    for index, block in enumerate(processing_data):
        if block.block_id == block_id:
            return index

    raise ValueError(
        f"No block with block_id {block_id} on the page you are in charge of."
    )


def _require_text(block: ProcessingBlock, block_id: int) -> ProcessingBlockText:
    """Returns block as a text block, rejecting any other kind."""
    if not isinstance(block, ProcessingBlockText):
        raise ValueError(
            f"Block {block_id} is not a text block. Label it as text before "
            "giving it a job only a text block can do."
        )

    return block


def _as[T: Order](order: Order, order_type: type[T]) -> T:
    """Returns order narrowed to the schema its order_label promises."""
    if not isinstance(order, order_type):
        raise TypeError(
            f"Order labeled {order.order_label} is not a {order_type.__name__}."
        )

    return order
