from dataclasses import asdict
from typing import Literal
from langchain_core.language_models import BaseChatModel
from ..OcrSchema import OcrResultBlockImage, OcrResultBlockText, OcrResultSection, OcrResultBlock, TEXT_BLOCK_TYPES
from ..LlmHelper import ImageBase64
from .Clipper import clip_image_with_agent


def find_block_by_index(
    index: int,
    section: OcrResultSection,
) -> OcrResultBlock:
    if section.block_index == index:
        return section

    for block in section.section_content:
        if block.block_index == index:
            return block

        if isinstance(block, OcrResultSection):
            try:
                return find_block_by_index(index, block)
            except KeyError:
                continue

    raise KeyError(f"Block with index {index} not found")

def get_max_block_index(section: OcrResultSection) -> int:
    max_index = section.block_index

    for block in section.section_content:
        if block.block_index > max_index:
            max_index = block.block_index

        if isinstance(block, OcrResultSection):
            child_max_index = get_max_block_index(block)
            if child_max_index > max_index:
                max_index = child_max_index

    return max_index

def find_section_by_index(
    index: int,
    section: OcrResultSection,
) -> OcrResultSection:
    if section.block_index == index:
        return section

    for block in section.section_content:
        if isinstance(block, OcrResultSection):
            try:
                return find_section_by_index(index, block)
            except KeyError:
                continue

    raise KeyError(f"Section with index {index} not found")

def mark_existing_page(
    entire_section: OcrResultSection,
    target_index: int,
    page_number: int,
) -> bool:
    """Adds page_number to existing_pages of the block with target_index and every ancestor section, including `section` itself. Returns whether target_index was found within `section`."""
    if entire_section.block_index == target_index:
        if page_number not in entire_section.existing_pages:
            entire_section.existing_pages.append(page_number)
        return True

    found = False
    for block in entire_section.section_content:
        if block.block_index == target_index:
            if page_number not in block.existing_pages:
                block.existing_pages.append(page_number)
            found = True
            break

        if isinstance(block, OcrResultSection) and mark_existing_page(block, target_index, page_number):
            found = True
            break

    if found and page_number not in entire_section.existing_pages:
        entire_section.existing_pages.append(page_number)

    return found

def iterate_sections(section: OcrResultSection):
    yield section

    for block in section.section_content:
        if isinstance(block, OcrResultSection):
            yield from iterate_sections(block)

def build_context_dict(
    section: OcrResultSection,
    current_page_number: int,
    recent_page_window: int = 1,
    truncate_length: int = 200,
) -> dict:
    """Serialize the section tree for the agent's prompt, truncating the text of
    blocks that are not on or near the current page. Without this, the full text
    of every block ever added is resent on every page, so context size grows
    without bound over the course of a long document."""
    content = []
    for block in section.section_content:
        if isinstance(block, OcrResultSection):
            content.append(build_context_dict(block, current_page_number, recent_page_window, truncate_length))
        elif isinstance(block, OcrResultBlockText):
            text = block.text
            is_recent = bool(block.existing_pages) and max(block.existing_pages) >= current_page_number - recent_page_window
            if not is_recent and len(text) > truncate_length:
                text = f"{text[:truncate_length]}... [truncated, {len(text)} chars total]"
            content.append({
                "block_type": block.block_type,
                "existing_pages": block.existing_pages,
                "block_index": block.block_index,
                "text": text,
            })
        else:
            content.append(asdict(block))

    return {
        "block_type": section.block_type,
        "existing_pages": section.existing_pages,
        "block_index": section.block_index,
        "section_content": content,
    }

class LinearTools:
    def __init__(
        self,
        all_pages: list[ImageBase64],
        ocr_entire_section: OcrResultSection,
        clipper_model: BaseChatModel,
    ) -> None:
        self.all_pages = all_pages
        self.ocr_entire_section = ocr_entire_section
        self.clipper_model = clipper_model
        self.current_page_number = -1  # 0-indexed

    def set_current_page(
        self,
        page_number: int,
    ) -> str:
        """Set the page number currently being processed."""
        if page_number < 0 or page_number >= len(self.all_pages):
            return f"ERROR: Invalid page number. The page number must be between 0 and {len(self.all_pages) - 1}"

        self.current_page_number = page_number
        return f"Current page set to {page_number}"

    def get_page_image(self, page_number: int):
        """Get the image of the specified page number."""
        if page_number < 0 or page_number >= len(self.all_pages):
            return f"ERROR: Invalid page number. The page number must be between 0 and {len(self.all_pages) - 1}"

        img_b64 = self.all_pages[page_number].b64

        return [
            {
                "type": "text",
                "text": f"this is the image of page {page_number}"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_b64}",
                }
            }
        ]

    def edit_block(
        self,
        block_index: int,
        text: str,
    ) -> str:
        """Edit the text of an existing block by its index."""
        try:
            block = find_block_by_index(block_index, self.ocr_entire_section)
        except KeyError:
            return f"ERROR: Block with index {block_index} not found"

        if not isinstance(block, OcrResultBlockText):
            return f"ERROR: Block with index {block_index} is not a text block"

        block.text = text
        mark_existing_page(self.ocr_entire_section, block_index, self.current_page_number)
        return f"Block with index {block_index} has been updated successfully. The new text is: \n{text}"

    def add_text_block(
        self,
        section_block_index: int,
        block_type: TEXT_BLOCK_TYPES,
        text: str,
    ) -> str:
        """Add a new text block to the specified section."""
        try:
            section = find_section_by_index(section_block_index, self.ocr_entire_section)
        except KeyError:
            return f"ERROR: Section with index {section_block_index} not found"

        new_block_index = get_max_block_index(self.ocr_entire_section) + 1
        new_block = OcrResultBlockText(
            block_type=block_type,
            existing_pages=[],
            block_index=new_block_index,
            text=text,
        )
        section.section_content.append(new_block)
        mark_existing_page(self.ocr_entire_section, new_block_index, self.current_page_number)

        return f"New text block added to section {section_block_index} with block index {new_block_index}. The text is: \n{text}"

    def add_image_block(
        self,
        section_block_index: int,
        bounding_box: tuple[int, int, int, int],
        caption: str,
    ) -> str:
        """Add a new image block to the specified section. bounding_box must be in the pixel coordinates of the current page (as set by set_current_page)."""
        if self.current_page_number == -1:
            return "ERROR: Current page is not set. Please set the current page first."

        try:
            section = find_section_by_index(section_block_index, self.ocr_entire_section)
        except KeyError:
            return f"ERROR: Section with index {section_block_index} not found"

        new_block_index = get_max_block_index(self.ocr_entire_section) + 1
        new_block = OcrResultBlockImage(
            block_type="image",
            existing_pages=[],
            block_index=new_block_index,
            page_number=self.current_page_number,
            bounding_box=bounding_box,
            caption=caption
        )
        section.section_content.append(new_block)
        mark_existing_page(self.ocr_entire_section, new_block_index, self.current_page_number)

        return f"New image block added to section {section_block_index} with block index {new_block_index}. The caption is: \n{caption}"

    def add_section(
        self,
        parent_section_block_index: int,
    ) -> str:
        """Add a new empty section under the specified parent section."""
        try:
            parent_section = find_section_by_index(parent_section_block_index, self.ocr_entire_section)
        except KeyError:
            return f"ERROR: Section with index {parent_section_block_index} not found"

        new_section_index = get_max_block_index(self.ocr_entire_section) + 1
        new_section = OcrResultSection(
            block_type="section",
            existing_pages=[],
            block_index=new_section_index,
            section_content=[],
        )
        parent_section.section_content.append(new_section)
        mark_existing_page(self.ocr_entire_section, new_section_index, self.current_page_number)

        return f"New section added to parent section {parent_section_block_index} with section index {new_section_index}"

    def move_block(
        self,
        block_index_target: int,
        destination_section_block_index: int,
        block_number_destination: int | None = None, # if None, append to the end of the section
    ) -> str:
        """Move a block to a different section and position. block_number_destination is the index the block should end up at within the destination section's content list."""
        # Find the block and its parent section
        parent_section = None
        block_to_move = None
        block_index_in_parent = None

        for section in iterate_sections(self.ocr_entire_section):
            for i, block in enumerate(section.section_content):
                if block.block_index == block_index_target:
                    parent_section = section
                    block_to_move = block
                    block_index_in_parent = i
                    break
            if block_to_move is not None:
                break

        if block_to_move is None:
            return f"ERROR: Block with index {block_index_target} not found"

        # A section can't be moved into itself or one of its own descendants
        if isinstance(block_to_move, OcrResultSection):
            if any(
                sub_section.block_index == destination_section_block_index
                for sub_section in iterate_sections(block_to_move)
            ):
                return f"ERROR: Cannot move section {block_index_target} into itself or one of its own descendant sections"

        # Find destination section
        try:
            destination_section = find_section_by_index(destination_section_block_index, self.ocr_entire_section)
        except KeyError:
            return f"ERROR: Section with index {destination_section_block_index} not found"

        # Remove block from parent section
        parent_section.section_content.pop(block_index_in_parent)

        # Insert block into destination section
        if block_number_destination is None:
            destination_section.section_content.append(block_to_move)
            position_str = "end"
        else:
            if block_number_destination < 0 or block_number_destination > len(destination_section.section_content):
                return f"ERROR: Invalid block_number_destination {block_number_destination}. Must be between 0 and {len(destination_section.section_content)}"
            destination_section.section_content.insert(block_number_destination, block_to_move)
            position_str = str(block_number_destination)

        return f"Block with index {block_index_target} has been moved to section {destination_section_block_index} at position {position_str}"

    def clip_image(
        self,
        order: str,
    ) -> str:
        """Clip a region of the current page's image according to `order`, and return its bounding box."""
        if self.current_page_number == -1:
            return "ERROR: Current page is not set. Please set the current page first."

        current_page = self.all_pages[self.current_page_number]

        result = clip_image_with_agent(self.clipper_model, order, current_page.b64, current_page.size)

        return f"Clipped bounding box: {result.bounding_box}"
