"""Settling one page's structure: the model round-trips that label and order its blocks."""

import json
import logging
from copy import deepcopy
from dataclasses import asdict
from PIL.Image import Image
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.messages.content import create_text_block
from ...LlmHelper import build_image_message, pil_to_base64
from .ProcessingSchema import ProcessingBlock
from .OrderSchema import OrderBatch
from .OrganizeExecutor import execute_orders
from .prompt import ORGANIZER_AGENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# How many already-handled pages are shown alongside the current one. A block
# splits across a page boundary, and a heading's level depends on the headings
# above it, so the pages just before matter; the whole document does not fit.
RECENT_PAGE_COUNT = 3

# Guard against a model that never sets is_last_batch, not a budget for a
# normal page.
MAX_BATCH_COUNT = 10


class OrganizerAgent:
    """Runs one page through the organizer model, applying the orders it gives
    until the model reports the page is done.

    The model works in batches rather than one final answer: it may ask to see
    what its orders did before deciding what else the page needs. A batch that
    cannot be applied is handed back for the model to correct, and leaves the
    blocks untouched."""

    def __init__(
        self,
        organizer_model: BaseChatModel,
    ) -> None:
        """
        Args:
            organizer_model: Multimodal chat model that issues the orders.
        """
        self.organizer_model = organizer_model.with_structured_output(OrderBatch)

    def scan_page(
        self,
        page_number: int,  # 1-indexed
        page_image: Image,
        page_image_rendered: Image,
        page_images_former: list[Image],
        processing_blocks: list[ProcessingBlock],
    ) -> None:
        """Settles the structure of one page, editing processing_blocks in place.

        Args:
            page_number: The 1-indexed page being settled.
            page_image: The page as it was scanned.
            page_image_rendered: The same page with the detected blocks drawn on top.
            page_images_former: The images of the pages just before this one,
                oldest first, at most RECENT_PAGE_COUNT of them.
            processing_blocks: Every block of the document, in current order.
                Only this page's blocks and those of the pages just before it
                are shown to the model, but an order may reach any of them.
        """
        messages = self._build_messages(
            page_number=page_number,
            page_image=page_image,
            page_image_rendered=page_image_rendered,
            page_images_former=page_images_former,
            processing_blocks=processing_blocks,
        )

        for batch_number in range(1, MAX_BATCH_COUNT + 1):
            order_batch = self._request_orders(messages, page_number, batch_number)
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
                    "page %d | batch %d rejected: %s", page_number, batch_number, error
                )
                messages.append(HumanMessage(content=_rejection_message(error)))
                continue

            processing_blocks[:] = edited_blocks

            # if the model indicated to finish...
            if order_batch.is_last_batch:
                # ...finish loop
                logger.info("page %d | done", page_number)
                return

            # ...otherwise show what the orders did and let it continue
            messages.append(
                HumanMessage(
                    content=_continuation_message(page_number, processing_blocks)
                )
            )

        logger.warning(
            "page %d | gave up after %d batches without is_last_batch",
            page_number,
            MAX_BATCH_COUNT,
        )

    def _request_orders(
        self,
        messages: list[BaseMessage],
        page_number: int,
        batch_number: int,
    ) -> OrderBatch:
        """Asks the model for the next batch of orders."""
        order_batch = self.organizer_model.invoke(messages)

        if not isinstance(order_batch, OrderBatch):
            raise RuntimeError(
                f"Page {page_number}: the organizer model returned no order batch."
            )

        logger.info(
            "page %d | batch %d: %d order(s), is_last_batch=%s",
            page_number,
            batch_number,
            len(order_batch.orders),
            order_batch.is_last_batch,
        )

        return order_batch

    def _build_messages(
        self,
        page_number: int,  # 1-indexed
        page_image: Image,
        page_image_rendered: Image,
        page_images_former: list[Image],
        processing_blocks: list[ProcessingBlock],
    ) -> list[BaseMessage]:
        """The system prompt plus the page's images and current block state."""
        content: list[dict] = []

        # the pages already handled, oldest first, for context only
        first_former_page_number = page_number - len(page_images_former)
        for offset, former_image in enumerate(page_images_former):
            content += build_image_message(
                f"Page {first_former_page_number + offset}, already handled, for context only:",
                pil_to_base64(former_image),
            )

        content += build_image_message(
            f"Page {page_number}, the page you are in charge of:",
            pil_to_base64(page_image),
        )
        content += build_image_message(
            f"Page {page_number} again, with each detected block outlined and labeled with its block_id:",
            pil_to_base64(page_image_rendered),
        )
        content.append(
            create_text_block(_block_state_text(page_number, processing_blocks))
        )

        return [
            SystemMessage(
                content=ORGANIZER_AGENT_SYSTEM_PROMPT.format(page_number=page_number)
            ),
            HumanMessage(content=content),
        ]


def _block_state_text(
    page_number: int,  # 1-indexed
    processing_blocks: list[ProcessingBlock],
) -> str:
    """The blocks of this page and the pages just before it, as JSON."""
    return (
        "The current state of the blocks, in their current order:\n"
        f"{_build_blocks_context_string(page_number, processing_blocks)}"
    )


def _build_blocks_context_string(
    page_number: int,  # 1-indexed
    processing_blocks: list[ProcessingBlock],
) -> str:
    """The blocks the model is shown, as JSON, in their current order.

    Kept to this page and the RECENT_PAGE_COUNT pages before it: the rest of
    the document is already settled, and resending it grows with every page.
    """
    # ProcessingBlock.page_number is 0-indexed, page_number is not
    current_page_index = page_number - 1
    shown_pages = range(
        max(0, current_page_index - RECENT_PAGE_COUNT), current_page_index + 1
    )

    shown_blocks = [
        _block_to_dict(block)
        for block in processing_blocks
        if block.page_number in shown_pages
    ]

    # compact separators: this is resent with every batch
    return json.dumps(shown_blocks, ensure_ascii=False, separators=(",", ":"))


def _block_to_dict(block: ProcessingBlock) -> dict:
    """One block as the model sees it, page numbers shown 1-indexed."""
    block_dict = asdict(block)
    block_dict["page_number"] = block.page_number + 1
    return block_dict


def _rejection_message(error: Exception) -> str:
    """What the model is told when its batch could not be applied."""
    return (
        "Your orders could not be applied, and none of them were recorded, so "
        "the blocks are exactly as they were before your last answer. Fix this "
        f"problem and send the batch again:\n- {error}"
    )


def _continuation_message(
    page_number: int,  # 1-indexed
    processing_blocks: list[ProcessingBlock],
) -> str:
    """What the model is told when it asked to see its orders' result."""
    return (
        "Your orders were applied.\n"
        f"{_block_state_text(page_number, processing_blocks)}\n"
        f"Continue with page {page_number}, and set is_last_batch to true once it is done."
    )
