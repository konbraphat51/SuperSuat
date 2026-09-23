"""Settling one page's structure: the model round-trips that label and order its blocks."""

import json
import logging
from copy import deepcopy
from dataclasses import asdict
from PIL.Image import Image
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.messages.content import create_text_block
from ....LlmHelper import build_image_message, pil_to_base64
from ..ProcessingSchema import (
    ProcessingBlock,
    ProcessingBlockText,
    ProcessingBlockFigure,
)
from .OrderSchema import OrderBatch
from .ClassificationExecutor import execute_orders
from .prompt import CLASSIFIER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# How many already-handled pages are shown alongside the current one.
RECENT_PAGE_COUNT = 1

# How many pages of block state are shown, alongside the current page. A
# block continues across one page boundary, which is all this has to cover.
BLOCK_STATE_FORMER_PAGE_COUNT = 1

# Guard against a model that never sets is_last_batch
MAX_BATCH_COUNT = 10


class Classifier:
    """Runs one page through the classifier model, applying the orders it gives
    until the model reports the page is done.

    The model works in batches rather than one final answer: it may ask to see
    what its orders did before deciding what else the page needs. A batch that
    cannot be applied is handed back for the model to correct, and leaves the
    blocks untouched."""

    def __init__(
        self,
        classifier_model: BaseChatModel,
    ) -> None:
        """
        Args:
            classifier_model: Multimodal chat model that issues the orders.
        """
        self.classifier_model = classifier_model.with_structured_output(OrderBatch)

    def scan_page(
        self,
        page_index: int,
        all_page_images: list[Image],
        page_image_rendered: Image,
        processing_blocks: list[ProcessingBlock],
    ) -> None:
        """Settles the structure of one page, editing processing_blocks in place.

        Args:
            page_index: The page being settled, 0-indexed. Every page number
                shown to the model is this plus one, since a reader counts
                pages from 1.
            all_page_images: Every page of the document, as scanned, 0-indexed.
                Only this page and the pages just before it are shown to the
                model.
            page_image_rendered: This page with the detected blocks drawn on top.
            processing_blocks: Every block of the document, in current order.
                Only this page's blocks and those of the pages just before it
                are shown to the model, but an order may reach any of them.
        """
        messages = self._build_messages(
            page_index=page_index,
            all_page_images=all_page_images,
            page_image_rendered=page_image_rendered,
            processing_blocks=processing_blocks,
        )

        for batch_number in range(1, MAX_BATCH_COUNT + 1):
            order_batch = self._request_orders(messages, page_index, batch_number)
            messages.append(AIMessage(content=order_batch.model_dump_json()))

            # apply to a copy, so a batch that fails halfway leaves nothing behind
            edited_blocks = deepcopy(processing_blocks)
            try:
                execute_orders(
                    order_batch=order_batch,
                    processing_data=edited_blocks,
                )
            except (ValueError, TypeError) as error:
                logger.warning(
                    "page %d | batch %d rejected: %s",
                    page_index + 1,
                    batch_number,
                    error,
                )
                messages.append(HumanMessage(content=_rejection_message(error)))
                continue

            processing_blocks[:] = edited_blocks

            # if the model indicated to finish...
            if order_batch.is_last_batch:
                # validate that the page is actually done
                is_done, message = self._is_able_to_finish(
                    page_index=page_index,
                    processing_blocks=processing_blocks,
                )
                if not is_done:
                    logger.warning(
                        "page %d | batch %d claimed done but is not: %s",
                        page_index + 1,
                        batch_number,
                        message,
                    )
                    messages.append(HumanMessage(content=message))
                    continue

                # the page is settled, so its blocks have been reviewed
                _mark_page_checked(page_index, processing_blocks)
                logger.info("page %d | done", page_index + 1)
                return

            # ...otherwise show what the orders did and let it continue
            messages.append(
                HumanMessage(
                    content=_continuation_message(page_index, processing_blocks)
                )
            )

        logger.warning(
            "page %d | gave up after %d batches without is_last_batch",
            page_index + 1,
            MAX_BATCH_COUNT,
        )

    def _request_orders(
        self,
        messages: list[BaseMessage],
        page_index: int,
        batch_number: int,
    ) -> OrderBatch:
        """Asks the model for the next batch of orders."""
        order_batch = self.classifier_model.invoke(messages)

        if not isinstance(order_batch, OrderBatch):
            raise RuntimeError(
                f"Page {page_index + 1}: the classifier model returned no order batch."
            )

        logger.info(
            "page %d | batch %d: %d order(s), is_last_batch=%s",
            page_index + 1,
            batch_number,
            len(order_batch.orders),
            order_batch.is_last_batch,
        )

        return order_batch

    def _build_messages(
        self,
        page_index: int,
        all_page_images: list[Image],
        page_image_rendered: Image,
        processing_blocks: list[ProcessingBlock],
    ) -> list[BaseMessage]:
        """The system prompt plus the page's images and current block state."""
        content: list[dict] = []

        # the pages just before this one, oldest first, for context only
        for former_page_index in _former_page_indices(page_index):
            content += build_image_message(
                f"Page {former_page_index + 1}, already handled, for context only:",
                pil_to_base64(all_page_images[former_page_index]),
            )

        # this page
        content += build_image_message(
            f"Page {page_index + 1}, the page you are in charge of:",
            pil_to_base64(all_page_images[page_index]),
        )
        content += build_image_message(
            f"Page {page_index + 1} again, with each detected block outlined and labeled with its block_id:",
            pil_to_base64(page_image_rendered),
        )
        content.append(
            create_text_block(_block_state_text(page_index, processing_blocks))
        )

        return [
            SystemMessage(
                content=CLASSIFIER_SYSTEM_PROMPT.format(page_number=page_index + 1)
            ),
            HumanMessage(content=content),
        ]

    def _is_able_to_finish(
        self,
        page_index: int,
        processing_blocks: list[ProcessingBlock],
    ) -> tuple[bool, str]:
        """Whether every block on the page is settled, and what is missing.

        Args:
            page_index: The page being checked, 0-indexed.
            processing_blocks: Every block of the document, in current order.

        Returns:
            (True, "") when the page is done, otherwise (False, message) with
            one line per problem, naming every block at fault.
        """
        page_blocks = [
            block for block in processing_blocks if block.page_index == page_index
        ]

        problems = [
            problem
            for problem in (
                _unlabeled_text_problem(page_blocks),
                _unchecked_figure_problem(page_blocks),
            )
            if problem is not None
        ]

        return not problems, "\n".join(problems)


def _unlabeled_text_problem(page_blocks: list[ProcessingBlock]) -> str | None:
    """The text blocks of the page still carrying no block_type, if any."""
    block_ids = [
        block.block_id
        for block in page_blocks
        if isinstance(block, ProcessingBlockText) and not block.have_been_labeled
    ]

    if not block_ids:
        return None

    return (
        f"These text blocks still have no block_type: {_list_ids(block_ids)}. "
        "Label each one."
    )


def _unchecked_figure_problem(page_blocks: list[ProcessingBlock]) -> str | None:
    """The figures of the page whose caption has not been checked, if any."""
    block_ids = [
        block.block_id
        for block in page_blocks
        if isinstance(block, ProcessingBlockFigure) and not block.have_caption_checked
    ]

    if not block_ids:
        return None

    return (
        f"These figures have not been checked for a caption yet: "
        f"{_list_ids(block_ids)}. Tie each one to the text block holding its caption."
    )


def _list_ids(block_ids: list[int]) -> str:
    """The block ids as one comma-separated list."""
    return ", ".join(str(block_id) for block_id in block_ids)


def _mark_page_checked(
    page_index: int,
    processing_blocks: list[ProcessingBlock],
) -> None:
    """Records that the page has been reviewed, on each of its blocks.

    A block merged into one on another page is gone by now, and a block moved
    here from another page is marked with this one - the mark says the block
    was looked at, not which page it started on.
    """
    for block in processing_blocks:
        if block.page_index == page_index:
            block.have_been_checked = True


def _former_page_indices(page_index: int) -> range:
    """The pages just before this one, oldest first."""
    return range(max(0, page_index - RECENT_PAGE_COUNT), page_index)


def _block_state_text(
    page_index: int,
    processing_blocks: list[ProcessingBlock],
) -> str:
    """The blocks of this page and the pages just before it, as JSON."""
    return (
        "The current state of the blocks, in their current order:\n"
        f"{_build_blocks_context_string(page_index, processing_blocks)}"
    )


def _build_blocks_context_string(
    page_index: int,
    processing_blocks: list[ProcessingBlock],
) -> str:
    """The blocks the model is shown, as JSON, in their current order.

    Kept to this page and the page before it: the rest of the document is
    already settled, and resending it grows with every page.
    """
    shown_pages = range(
        max(0, page_index - BLOCK_STATE_FORMER_PAGE_COUNT), page_index + 1
    )

    shown_blocks = [
        _block_to_dict(block)
        for block in processing_blocks
        if block.page_index in shown_pages
    ]

    # compact separators: this is resent with every batch
    return json.dumps(shown_blocks, ensure_ascii=False, separators=(",", ":"))


def _block_to_dict(block: ProcessingBlock) -> dict:
    """One block as the model sees it: page_index 0 is page_number 1, since a
    reader counts pages from 1."""
    return {
        ("page_number" if name == "page_index" else name): (
            value + 1 if name == "page_index" else value
        )
        for name, value in asdict(block).items()
    }


def _rejection_message(error: Exception) -> str:
    """What the model is told when its batch could not be applied."""
    return (
        "Your orders could not be applied, and none of them were recorded, so "
        "the blocks are exactly as they were before your last answer. Fix this "
        f"problem and send the batch again:\n- {error}"
    )


def _continuation_message(
    page_index: int,
    processing_blocks: list[ProcessingBlock],
) -> str:
    """What the model is told when it asked to see its orders' result."""
    return (
        "Your orders were applied.\n"
        f"{_block_state_text(page_index, processing_blocks)}\n"
        f"Continue with page {page_index + 1}, and set is_last_batch to true once it is done."
    )
