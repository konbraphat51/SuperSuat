"""Settling one page's structure: the model round-trips that label and order its blocks."""

import json
import logging
from copy import deepcopy

from PIL.Image import Image
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.messages.content import create_text_block

from ....LlmHelper import build_image_message, page_to_base64
from ..ProcessingSchema import (
    ProcessingBlock,
    ProcessingBlockFigure,
)
from .ClassificationExecutor import execute_orders
from .OrderSchema import OrderBatch
from .prompt import CLASSIFIER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# How many pages before the current one are shown alongside it.
RECENT_PAGE_COUNT = 1

# Guard against a model that never sets is_last_batch
MAX_BATCH_COUNT = 10


class Classifier:
    """Runs one page through the classifier model, applying the orders it gives
    until the model reports the page is done.

    Nothing has been read at this point: the model judges from the page image
    alone, which is what makes its answer worth having - it says what each
    block is, and only then is each block read as the kind of thing it is.

    The model works in batches rather than one final answer: it may ask to see
    what its orders did before deciding what else the page needs. A batch that
    cannot be applied is handed back for the model to correct, and leaves the
    blocks untouched.

    A page is settled on its own: the orders reach only that page's blocks, and
    the pages around it are context the model reads and cannot change. That is
    what lets the pages be classified in parallel."""

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
        page_blocks: list[ProcessingBlock],
        context_page_blocks: list[list[ProcessingBlock]],
    ) -> list[ProcessingBlock]:
        """Settles the structure of one page, editing page_blocks in place.

        Args:
            page_index: The page being settled, 0-indexed. Every page number
                shown to the model is this plus one, since a reader counts
                pages from 1.
            all_page_images: Every page of the document, as scanned, 0-indexed.
                Only this page and the pages just before it are shown.
            page_image_rendered: This page with the detected blocks drawn on top.
            page_blocks: This page's blocks, in current order. The orders act
                on these and on nothing else.
            context_page_blocks: Every page's blocks, one list per page, as
                they were before any page was settled. Only the pages just
                before this one are read from it - context for a block that
                spans the page boundary - and nothing in it is written, so the
                other pages may be settling at the same time.

        Returns:
            page_blocks, settled - the same list that was passed in.

        Raises:
            RuntimeError: The model gave no usable answer, or never reported
                the page done. The run stops there rather than writing down a
                page nobody settled.
        """
        former_page_blocks = _former_page_blocks(page_index, context_page_blocks)

        messages = self._build_messages(
            page_index=page_index,
            all_page_images=all_page_images,
            page_image_rendered=page_image_rendered,
            page_blocks=page_blocks,
            former_page_blocks=former_page_blocks,
        )

        for batch_number in range(1, MAX_BATCH_COUNT + 1):
            order_batch = self._request_orders(messages, page_index, batch_number)
            messages.append(AIMessage(content=order_batch.model_dump_json()))

            # apply to a copy, so a batch that fails halfway leaves nothing behind
            edited_blocks = deepcopy(page_blocks)
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

            page_blocks[:] = edited_blocks

            # if the model indicated to finish...
            if order_batch.is_last_batch:
                # validate that the page is actually done
                is_done, message = self._is_able_to_finish(page_blocks=page_blocks)
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
                _mark_page_checked(page_blocks)
                logger.info("page %d | done", page_index + 1)
                return page_blocks

            # ...otherwise show what the orders did and let it continue
            messages.append(
                HumanMessage(
                    content=_continuation_message(
                        page_index, page_blocks, former_page_blocks
                    )
                )
            )

        raise RuntimeError(
            f"Page {page_index + 1} was not settled in {MAX_BATCH_COUNT} batches."
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
        page_blocks: list[ProcessingBlock],
        former_page_blocks: list[ProcessingBlock],
    ) -> list[BaseMessage]:
        """The system prompt plus the page's images and current block state."""
        content: list[dict] = []

        # the pages just before this one, oldest first, for context only
        for former_page_index in _former_page_indices(page_index):
            content += build_image_message(
                f"Page {former_page_index + 1}, for context only:",
                page_to_base64(all_page_images[former_page_index]),
            )

        # this page
        content += build_image_message(
            f"Page {page_index + 1}, the page you are in charge of:",
            page_to_base64(all_page_images[page_index]),
        )
        content += build_image_message(
            f"Page {page_index + 1} again, with each detected block outlined and labeled with its block_id:",
            page_to_base64(page_image_rendered),
        )
        content.append(
            create_text_block(_block_state_text(page_blocks, former_page_blocks))
        )

        return [
            SystemMessage(
                content=CLASSIFIER_SYSTEM_PROMPT.format(page_number=page_index + 1)
            ),
            HumanMessage(content=content),
        ]

    def _is_able_to_finish(
        self,
        page_blocks: list[ProcessingBlock],
    ) -> tuple[bool, str]:
        """Whether every block on the page is settled, and what is missing.

        Args:
            page_blocks: This page's blocks, in current order.

        Returns:
            (True, "") when the page is done, otherwise (False, message) with
            one line per problem, naming every block at fault.
        """
        problems = [
            problem
            for problem in (
                _unlabeled_block_problem(page_blocks),
                _unchecked_figure_problem(page_blocks),
            )
            if problem is not None
        ]

        return not problems, "\n".join(problems)


def _unlabeled_block_problem(page_blocks: list[ProcessingBlock]) -> str | None:
    """The blocks of the page still carrying no block_type, if any."""
    block_ids = [block.block_id for block in page_blocks if not block.have_been_labeled]

    if not block_ids:
        return None

    return (
        f"These blocks still have no block_type: {_list_ids(block_ids)}. "
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


def _mark_page_checked(page_blocks: list[ProcessingBlock]) -> None:
    """Records that the page has been reviewed, on each of its blocks."""
    for block in page_blocks:
        block.have_been_checked = True


def _former_page_indices(page_index: int) -> range:
    """The pages just before this one, oldest first."""
    return range(max(0, page_index - RECENT_PAGE_COUNT), page_index)


def _former_page_blocks(
    page_index: int,
    context_page_blocks: list[list[ProcessingBlock]],
) -> list[ProcessingBlock]:
    """The blocks of the pages just before this one, in reading order."""
    return [
        block
        for former_page_index in _former_page_indices(page_index)
        for block in context_page_blocks[former_page_index]
    ]


def _block_state_text(
    page_blocks: list[ProcessingBlock],
    former_page_blocks: list[ProcessingBlock],
) -> str:
    """The blocks of this page and the pages just before it, as JSON."""
    return (
        "The current state of the blocks, in their current order:\n"
        f"{_build_blocks_context_string(page_blocks, former_page_blocks)}"
    )


def _build_blocks_context_string(
    page_blocks: list[ProcessingBlock],
    former_page_blocks: list[ProcessingBlock],
) -> str:
    """The blocks the model is shown, as JSON, in their current order.

    Kept to this page and the pages just before it: the rest of the document is
    another page's business, and resending it grows with every page.
    """
    shown_blocks = [_block_to_dict(block) for block in former_page_blocks + page_blocks]

    # compact separators: this is resent with every batch
    return json.dumps(shown_blocks, ensure_ascii=False, separators=(",", ":"))


def _block_to_dict(block: ProcessingBlock) -> dict:
    """One block as the model sees it.

    There is no text to show - nothing has been read yet - so a block is where
    it is on the page and what it has been called so far. page_index 0 is
    page_number 1, since a reader counts pages from 1.
    """
    shown = {
        "block_id": block.block_id,
        "page_number": block.page_index + 1,
        "bounding_box": list(block.bounding_box),
        "block_type": block.new_type,
    }

    if isinstance(block, ProcessingBlockFigure):
        shown["caption_block_id"] = block.caption_text_block_id
        shown["caption_checked"] = block.have_caption_checked

    return shown


def _rejection_message(error: Exception) -> str:
    """What the model is told when its batch could not be applied."""
    return (
        "Your orders could not be applied, and none of them were recorded, so "
        "the blocks are exactly as they were before your last answer. Fix this "
        f"problem and send the batch again:\n- {error}"
    )


def _continuation_message(
    page_index: int,
    page_blocks: list[ProcessingBlock],
    former_page_blocks: list[ProcessingBlock],
) -> str:
    """What the model is told when it asked to see its orders' result."""
    return (
        "Your orders were applied.\n"
        f"{_block_state_text(page_blocks, former_page_blocks)}\n"
        f"Continue with page {page_index + 1}, and set is_last_batch to true once it is done."
    )
