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
            content.append(asdict(block))
        else:
            omitted_pending = True

    if omitted_pending:
        content.append(OMITTED_MARKER)

    return {
        "block_type": section.block_type,
        "existing_pages": section.existing_pages,
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
    return json.dumps(context_dict, ensure_ascii=False, indent=2)
