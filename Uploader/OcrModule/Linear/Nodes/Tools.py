import base64
from typing import Literal
from io import BytesIO
from PIL.Image import Image
from ...OcrSchema import OcrResultBlockImage, OcrResultBlockText, OcrResultSection, OcrResultBlock, TEXT_BLOCK_TYPES

def pil_to_base64(img: Image, format: str = "PNG") -> str:
    buffered = BytesIO()
    img.save(buffered, format=format)
    img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_b64

def find_block_by_index(
    index: int,
    section: OcrResultSection,
) -> OcrResultBlock:
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

def iterate_sections(section: OcrResultSection):
    yield section

    for block in section.section_content:
        if isinstance(block, OcrResultSection):
            yield from iterate_sections(block)

class LinearTools:
    def __init__(
        self,
        all_page_images: list[Image],
        ocr_entire_section: OcrResultSection
    ) -> None:
        self.all_page_images = all_page_images
        self.ocr_entire_section = ocr_entire_section

    def get_page_image(self, page_number: int):
        if page_number < 0 or page_number >= len(self.all_page_images):
            return f"ERROR: Invalid page number. The page number must be between 0 and {len(self.all_page_images) - 1}"

        img = self.all_page_images[page_number]
        img_b64 = pil_to_base64(img)

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
        try:
            block = find_block_by_index(block_index, self.ocr_entire_section)
        except KeyError:
            return f"ERROR: Block with index {block_index} not found"

        if not isinstance(block, OcrResultBlock):
            return f"ERROR: Block with index {block_index} is not a text block"

        block.text = text
        return f"Block with index {block_index} has been updated successfully. The new text is: \n{text}"

    def add_text_block(
        self,
        section_index: int,
        block_type: TEXT_BLOCK_TYPES,
        text: str,
    ) -> str:
        try:
            section = find_section_by_index(section_index, self.ocr_entire_section)
        except KeyError:
            return f"ERROR: Section with index {section_index} not found"

        new_block_index = get_max_block_index(self.ocr_entire_section) + 1
        new_block = OcrResultBlockText(
            block_type=block_type,
            existing_pages=[],
            block_index=new_block_index,
            text=text,
        )
        section.section_content.append(new_block)

        return f"New text block added to section {section_index} with block index {new_block_index}. The text is: \n{text}"

    def add_image_block(
        self,
        section_index: int,
        bounding_box: tuple[int, int, int, int],
        caption: str,
    ) -> str:
        try:
            section = find_section_by_index(section_index, self.ocr_entire_section)
        except KeyError:
            return f"ERROR: Section with index {section_index} not found"

        new_block_index = get_max_block_index(self.ocr_entire_section) + 1
        new_block = OcrResultBlockImage(
            block_type="image",
            existing_pages=[],
            block_index=new_block_index,
            bounding_box=bounding_box,
            caption=caption
        )
        section.section_content.append(new_block)

        return f"New image block added to section {section_index} with block index {new_block_index}. The caption is: \n{caption}"

    def move_block(
        self,
        block_index_target: int,
        section_index_destination: int,
        block_number_destination: int | None = None, # if None, append to the end of the section
    ) -> str:
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

        # Find destination section
        try:
            destination_section = find_section_by_index(section_index_destination, self.ocr_entire_section)
        except KeyError:
            return f"ERROR: Section with index {section_index_destination} not found"

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

        return f"Block with index {block_index_target} has been moved to section {section_index_destination} at position {position_str}"

