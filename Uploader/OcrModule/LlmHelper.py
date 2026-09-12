import base64
import json
from dataclasses import asdict, dataclass
from io import BytesIO
from PIL.Image import Image

from .OcrSchema import OcrResultBlockText, OcrResultSection


@dataclass
class ImageBase64:
    b64: str
    size: tuple[int, int] # (width, height)

def pil_to_base64(img: Image, format: str = "PNG") -> str:
    buffered = BytesIO()
    img.save(buffered, format=format)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

OMITTED_MARKER = "... (omitted)"

def _find_section_path(section: OcrResultSection, target_section_index: int) -> list[OcrResultSection] | None:
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
    recent_pages = set(range(max(0, current_page_number - recent_page_count + 1), current_page_number + 1))
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
                    if isinstance(block, OcrResultBlockText) and block.block_type == "heading":
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

    return ",".join(str(first) if first == last else f"{first}-{last}" for first, last in ranges)

def _build_context_node(section: OcrResultSection, keep_indices: set[int]) -> dict:
    content: list = []
    omitted_pending = False

    for block in section.section_content:
        if isinstance(block, OcrResultSection):
            content.append(_build_context_node(block, keep_indices))
            continue

        if block.block_index in keep_indices:
            if omitted_pending:
                content.append(OMITTED_MARKER)
                omitted_pending = False

            block_dict = asdict(block)
            block_dict["existing_pages"] = format_existing_pages(block.existing_pages)
            content.append(block_dict)
        else:
            omitted_pending = True

    if omitted_pending:
        content.append(OMITTED_MARKER)

    return {
        "block_type": section.block_type,
        "existing_pages": format_existing_pages(section.existing_pages),
        "block_index": section.block_index,
        "section_content": content,
    }

def build_ocr_context_string(
    root_section: OcrResultSection,
    current_page_number: int,
    recent_page_count: int = 5,
) -> str:
    """Serialize the OCR result tree to a JSON string for the agent's prompt,
    bounding context growth on long documents by keeping only:
    - blocks on one of the most recent `recent_page_count` pages (including
      the current one)
    - the heading block of every section that directly holds a block from
      the page right before the current one, and of all its ancestor
      sections up to the root, so the document structure around what was
      just read stays visible
    Everything else is replaced with an ellipsis marker."""
    keep_indices = _collect_keep_block_indices(root_section, current_page_number, recent_page_count)
    context_dict = _build_context_node(root_section, keep_indices)
    # compact separators rather than indentation: the scaffolding of a document
    # with many sections is resent on every page, and indenting it roughly
    # doubles that cost for no gain to the model reading it
    return json.dumps(context_dict, ensure_ascii=False, separators=(",", ":"))
