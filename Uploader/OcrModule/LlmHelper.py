"""Shared plumbing for talking to a model: images, context, and logging."""

import base64
import json
import logging
from dataclasses import asdict, dataclass
from io import BytesIO
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.messages.content import create_image_block, create_text_block
from PIL.Image import Image

from .OcrSchema import OcrResultBlockText, OcrResultSection

logger = logging.getLogger(__name__)


@dataclass
class ImageBase64:
    """One page image, ready to put into a message."""

    b64: str
    size: tuple[int, int]  # (width, height)


def pil_to_base64(img: Image, format: str = "PNG") -> str:
    """The image as a base64 string, as message content carries it."""
    buffered = BytesIO()
    img.save(buffered, format=format)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def build_image_message(text: str | None, img_b64: str) -> list[dict]:
    """Text + PNG image content as provider-agnostic standard content blocks
    (langchain_core.messages.content), which every chat model integration
    translates to its own wire format."""
    blocks: list[dict] = []
    if text is not None:
        blocks.append(create_text_block(text))
    blocks.append(create_image_block(base64=img_b64, mime_type="image/png"))
    return blocks


OMITTED_MARKER = "... (omitted)"


def _find_section_path(
    section: OcrResultSection, target_section_index: int
) -> list[OcrResultSection] | None:
    """The chain of sections from `section` down to the section with
    `target_section_index`, inclusive of both ends, or None if not found."""
    if section.block_index == target_section_index:
        return [section]

    for block in section.section_content:
        if isinstance(block, OcrResultSection):
            sub_path = _find_section_path(block, target_section_index)
            if sub_path is not None:
                return [section] + sub_path

    return None


def _collect_keep_block_indices(
    root_section: OcrResultSection,
    current_page_number: int,
    recent_page_count: int,
) -> set[int]:
    """Block indices to keep in full: blocks on one of the most recent
    `recent_page_count` pages, plus the heading blocks of every section that
    directly holds a block from the page right before the current one, and of
    all that section's ancestors up to the root."""
    recent_pages = set(
        range(
            max(0, current_page_number - recent_page_count + 1),
            current_page_number + 1,
        )
    )
    previous_page = current_page_number - 1

    keep_indices: set[int] = set()

    def visit(section: OcrResultSection) -> None:
        has_previous_page_block = False

        for block in section.section_content:
            if isinstance(block, OcrResultSection):
                visit(block)
                continue

            if set(block.existing_pages) & recent_pages:
                keep_indices.add(block.block_index)

            if previous_page in block.existing_pages:
                has_previous_page_block = True

        if has_previous_page_block:
            path = _find_section_path(root_section, section.block_index) or [section]
            for ancestor in path:
                for block in ancestor.section_content:
                    if (
                        isinstance(block, OcrResultBlockText)
                        and block.block_type == "heading"
                    ):
                        keep_indices.add(block.block_index)

    visit(root_section)
    return keep_indices


def format_existing_pages(pages: list[int]) -> str:
    """Collapses a page list into range notation ("0-3,7"). A section near the
    end of a long document is present on every page seen so far, which costs
    one entry per page if written out as a list."""
    if not pages:
        return ""

    ordered = sorted(set(pages))
    ranges: list[tuple[int, int]] = []
    start = previous = ordered[0]

    for page in ordered[1:]:
        if page == previous + 1:
            previous = page
            continue

        ranges.append((start, previous))
        start = previous = page

    ranges.append((start, previous))

    return ",".join(
        str(first) if first == last else f"{first}-{last}" for first, last in ranges
    )


def _context_node(section: OcrResultSection, content: list) -> dict:
    return {
        "block_type": section.block_type,
        "existing_pages": format_existing_pages(section.existing_pages),
        "block_index": section.block_index,
        "section_content": content,
    }


def _build_context_node(
    section: OcrResultSection, keep_indices: set[int]
) -> dict | None:
    """The section as it should appear in the context, or None if nothing in it
    survived, in which case the whole node collapses into the ellipsis of the
    section holding it. A section with no contents at all is still returned:
    there is nothing to omit, and it stays addressable for adding blocks to."""
    content: list = []
    omitted_pending = False
    kept_anything = False

    for block in section.section_content:
        if isinstance(block, OcrResultSection):
            child_node = _build_context_node(block, keep_indices)
            if child_node is None:
                omitted_pending = True
                continue
        elif block.block_index in keep_indices:
            child_node = asdict(block)
            child_node["existing_pages"] = format_existing_pages(block.existing_pages)
        else:
            omitted_pending = True
            continue

        if omitted_pending:
            content.append(OMITTED_MARKER)
            omitted_pending = False

        content.append(child_node)
        kept_anything = True

    if not kept_anything and section.section_content:
        return None

    if omitted_pending:
        content.append(OMITTED_MARKER)

    return _context_node(section, content)


def build_ocr_context_string(
    root_section: OcrResultSection,
    current_page_number: int,
    recent_page_count: int = 5,
) -> str:
    """The document tree as JSON for the agent's prompt, kept small enough to
    resend with every page.

    Keeps blocks from the last `recent_page_count` pages, plus the headings of
    the sections around what was just read so the structure stays visible.
    Everything else collapses into an ellipsis marker."""
    keep_indices = _collect_keep_block_indices(
        root_section, current_page_number, recent_page_count
    )
    # the root never collapses, since it is the document itself
    context_dict = _build_context_node(root_section, keep_indices) or _context_node(
        root_section, [OMITTED_MARKER]
    )
    # compact separators: this is resent on every page, and indenting it roughly doubles the cost
    return json.dumps(context_dict, ensure_ascii=False, separators=(",", ":"))


def stringify_message_content(content) -> str:
    """A message's content as one log-friendly string.

    Text is kept as-is and reasoning is kept in <thinking> tags; an image
    becomes a placeholder so a page never lands in the log as base64, and a
    tool_use block is dropped since AIMessage.tool_calls already logs it."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for block in content:
            if not isinstance(block, dict):
                parts.append(str(block))
                continue

            block_type = block.get("type")
            if block_type == "text":
                parts.append(block.get("text", ""))
            elif block_type == "reasoning_content":
                reasoning = (
                    block.get("reasoning_content")
                    or block.get("reasoningContent")
                    or {}
                )
                reasoning_text = reasoning.get("text", "")
                if reasoning_text:
                    parts.append(f"<thinking>{reasoning_text}</thinking>")
            elif block_type in ("image", "image_url"):
                parts.append("<image>")
            elif block_type == "tool_use":
                continue
            else:
                parts.append(str(block))

        return " ".join(part for part in parts if part)

    return str(content)


def log_agent_message(label: str, message: BaseMessage) -> None:
    """Logs one message from an agent run - token usage, the model's text, and
    every tool call and result - prefixed with `label` (e.g. "page 3")."""
    if isinstance(message, AIMessage):
        usage = message.usage_metadata
        if usage:
            # every turn resends the whole conversation, so input tokens grow per round-trip
            logger.info(
                "%s | usage: input=%s output=%s total=%s",
                label,
                usage.get("input_tokens"),
                usage.get("output_tokens"),
                usage.get("total_tokens"),
            )
        text = stringify_message_content(message.content)
        if text:
            logger.info("%s | model: %s", label, text)
        for tool_call in message.tool_calls or []:
            logger.info(
                "%s | tool call: %s(%s)",
                label,
                tool_call["name"],
                tool_call["args"],
            )
    elif isinstance(message, ToolMessage):
        logger.info(
            "%s | tool result (%s): %s",
            label,
            message.name,
            stringify_message_content(message.content),
        )
