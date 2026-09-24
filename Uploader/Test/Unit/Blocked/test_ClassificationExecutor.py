"""Tests for the orders a Classifier issues being applied to the blocks."""

import pytest

from OcrModule.Blocked.StructureOrganizer.Classifier.ClassificationExecutor import (
    execute_orders,
)
from OcrModule.Blocked.StructureOrganizer.Classifier.OrderSchema import OrderBatch
from OcrModule.Blocked.StructureOrganizer.ProcessingSchema import (
    ProcessingBlock,
    ProcessingBlockFigure,
    ProcessingBlockText,
    ProcessingBlockTextHeading,
)


def make_blocks(count: int, page_index: int = 0) -> list[ProcessingBlock]:
    """`count` unlabeled blocks of one page, as the Blocker leaves them."""
    return [
        ProcessingBlock(
            block_id=block_id,
            page_index=page_index,
            bounding_box=(0, 10 * block_id, 100, 10),
        )
        for block_id in range(count)
    ]


def apply(blocks: list[ProcessingBlock], *orders: dict) -> None:
    """Applies the orders, as the model would send them."""
    execute_orders(
        OrderBatch.model_validate({"orders": list(orders), "is_last_batch": True}),
        blocks,
    )


def set_block_type(block_id: int, label: str) -> dict:
    return {
        "order_label": "set_block_type",
        "target_block_id": block_id,
        "new_label": label,
    }


def test_labeling_turns_a_block_into_the_kind_its_label_calls_for():
    blocks = make_blocks(3)

    apply(
        blocks,
        set_block_type(0, "heading"),
        set_block_type(1, "paragraph"),
        set_block_type(2, "figure"),
    )

    assert isinstance(blocks[0], ProcessingBlockTextHeading)
    assert type(blocks[1]) is ProcessingBlockText
    assert isinstance(blocks[2], ProcessingBlockFigure)
    assert [block.new_type for block in blocks] == ["heading", "paragraph", "figure"]
    assert all(block.have_been_labeled for block in blocks)


def test_a_heading_called_a_paragraph_stops_being_a_heading():
    blocks = make_blocks(1)

    apply(blocks, set_block_type(0, "heading"))
    apply(blocks, set_block_type(0, "paragraph"))

    assert not isinstance(blocks[0], ProcessingBlockTextHeading)
    assert blocks[0].new_type == "paragraph"


def test_a_relabeled_block_keeps_what_the_new_kind_also_holds():
    blocks = make_blocks(1)

    apply(blocks, set_block_type(0, "paragraph"))
    blocks[0].merging_previous_page = False
    apply(blocks, set_block_type(0, "heading"))

    assert blocks[0].block_id == 0
    assert blocks[0].bounding_box == (0, 0, 100, 10)
    assert blocks[0].have_been_labeled


def test_reorder_moves_a_block_in_front_of_another():
    blocks = make_blocks(3)

    apply(
        blocks, {"order_label": "reorder", "target_block_id": 2, "to_in_front_of_block_id": 0}
    )

    assert [block.block_id for block in blocks] == [2, 0, 1]


def test_an_order_naming_an_unknown_block_is_rejected_and_changes_nothing():
    blocks = make_blocks(2)

    with pytest.raises(ValueError, match="block_id 9"):
        apply(
            blocks,
            {
                "order_label": "reorder",
                "target_block_id": 1,
                "to_in_front_of_block_id": 9,
            },
        )

    assert [block.block_id for block in blocks] == [0, 1]


def test_deleting_a_block_clears_the_caption_pointing_at_it():
    blocks = make_blocks(2)
    apply(
        blocks,
        set_block_type(0, "figure"),
        set_block_type(1, "paragraph"),
        {
            "order_label": "set_caption",
            "target_image_block_id": 0,
            "target_caption_block_id": 1,
        },
    )

    apply(blocks, {"order_label": "delete_block", "target_block_id": 1})

    assert len(blocks) == 1
    assert blocks[0].caption_text_block_id is None
    assert not blocks[0].have_caption_checked


def test_a_figure_with_no_caption_still_counts_as_checked():
    blocks = make_blocks(1)

    apply(
        blocks,
        set_block_type(0, "figure"),
        {
            "order_label": "set_caption",
            "target_image_block_id": 0,
            "target_caption_block_id": None,
        },
    )

    assert blocks[0].have_caption_checked
    assert blocks[0].caption_text_block_id is None


def test_captioning_something_that_is_not_a_figure_is_rejected():
    blocks = make_blocks(2)
    apply(blocks, set_block_type(0, "paragraph"), set_block_type(1, "paragraph"))

    with pytest.raises(ValueError, match="not a figure block"):
        apply(
            blocks,
            {
                "order_label": "set_caption",
                "target_image_block_id": 0,
                "target_caption_block_id": 1,
            },
        )


def test_the_first_page_cannot_continue_a_previous_page():
    blocks = make_blocks(1, page_index=0)
    apply(blocks, set_block_type(0, "paragraph"))

    with pytest.raises(ValueError, match="first page"):
        apply(
            blocks,
            {
                "order_label": "set_merging_previous_page",
                "target_block_id": 0,
                "merging_previous_page": True,
            },
        )
