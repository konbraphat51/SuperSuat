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
from .ProcessingSchema import ProcessingBlock, ProcessingBlockTextHeading
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
                Only a few of them are shown to the model: this page, the pages
                just before it, and the page of each heading it sits under.
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
                # ...finish loop
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
        order_batch = self.organizer_model.invoke(messages)

        if not isinstance(order_batch, OrderBatch):
            raise RuntimeError(
                f"Page {page_index + 1}: the organizer model returned no order batch."
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
        shown_page_indices: set[int] = {page_index}

        # where in the document this page sits: the page of each heading still
        # open when the previous page ended, outermost heading first. Several
        # of those headings can share a page, which is then sent once.
        ancestor_headings = _collect_ancestor_headings(page_index, processing_blocks)
        for heading_page_index, headings in _group_by_page(ancestor_headings):
            shown_page_indices.add(heading_page_index)
            content += build_image_message(
                f"Page {heading_page_index + 1}, holding {_describe_headings(headings)} "
                "this page is still under:",
                pil_to_base64(all_page_images[heading_page_index]),
            )

        # the pages just before this one, oldest first, for context only
        for former_page_index in _former_page_indices(page_index):
            if former_page_index in shown_page_indices:
                continue

            shown_page_indices.add(former_page_index)
            content += build_image_message(
                f"Page {former_page_index + 1}, already handled, for context only:",
                pil_to_base64(all_page_images[former_page_index]),
            )

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
                content=ORGANIZER_AGENT_SYSTEM_PROMPT.format(page_number=page_index + 1)
            ),
            HumanMessage(content=content),
        ]


def _former_page_indices(page_index: int) -> range:
    """The pages just before this one, oldest first."""
    return range(max(0, page_index - RECENT_PAGE_COUNT), page_index)


def _collect_ancestor_headings(
    page_index: int,
    processing_blocks: list[ProcessingBlock],
) -> list[ProcessingBlockTextHeading]:
    """The headings still open when the page before this one ended, outermost
    first.

    That is the last heading before this page, then the nearest heading above
    it of a lower level, and so on up to level 1 - the chapter and section this
    page's content is sitting inside. A heading of a level already covered is
    a sibling that has since been closed, so it is skipped.
    """
    ancestors: list[ProcessingBlockTextHeading] = []
    innermost_level: int | None = None

    # walk backwards from the page before this one
    for block in reversed(processing_blocks):
        if block.page_number >= page_index:
            continue

        if not isinstance(block, ProcessingBlockTextHeading):
            continue

        if block.heading_level is None:
            continue

        if innermost_level is not None and block.heading_level >= innermost_level:
            continue

        ancestors.append(block)
        innermost_level = block.heading_level

        # nothing sits above the document's own title
        if innermost_level <= 1:
            break

    return list(reversed(ancestors))


def _group_by_page(
    headings: list[ProcessingBlockTextHeading],
) -> list[tuple[int, list[ProcessingBlockTextHeading]]]:
    """The headings grouped by the page they are on, each page once, in the
    order the pages first appear in the list."""
    grouped: dict[int, list[ProcessingBlockTextHeading]] = {}

    for heading in headings:
        grouped.setdefault(heading.page_number, []).append(heading)

    return list(grouped.items())


def _describe_headings(headings: list[ProcessingBlockTextHeading]) -> str:
    """The headings named as one phrase, for the label of their page image."""
    described = [
        f'the level {heading.heading_level} heading "{heading.text}"'
        for heading in headings
    ]

    if len(described) == 1:
        return described[0]

    return f"{', '.join(described[:-1])} and {described[-1]}"


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

    Kept to this page and the RECENT_PAGE_COUNT pages before it: the rest of
    the document is already settled, and resending it grows with every page.
    """
    shown_pages = range(max(0, page_index - RECENT_PAGE_COUNT), page_index + 1)

    shown_blocks = [
        _block_to_dict(block)
        for block in processing_blocks
        if block.page_number in shown_pages
    ]

    # compact separators: this is resent with every batch
    return json.dumps(shown_blocks, ensure_ascii=False, separators=(",", ":"))


def _block_to_dict(block: ProcessingBlock) -> dict:
    """One block as the model sees it, its page counted from 1."""
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
    page_index: int,
    processing_blocks: list[ProcessingBlock],
) -> str:
    """What the model is told when it asked to see its orders' result."""
    return (
        "Your orders were applied.\n"
        f"{_block_state_text(page_index, processing_blocks)}\n"
        f"Continue with page {page_index + 1}, and set is_last_batch to true once it is done."
    )
