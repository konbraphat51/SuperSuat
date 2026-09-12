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

    for child_section in section.child_sections:
        try:
            return find_block_by_index(index, child_section)
        except KeyError:
            continue

    raise KeyError(f"Block with index {index} not found")

def get_max_block_index(section: OcrResultSection) -> int:
    max_index = -1

    for block in section.section_content:
        if block.block_index > max_index:
            max_index = block.block_index

    for child_section in section.child_sections:
        child_max_index = get_max_block_index(child_section)
        if child_max_index > max_index:
            max_index = child_max_index

    return max_index

def find_section_by_index(
    index: int,
    section: OcrResultSection,
) -> OcrResultSection:
    if section.section_index == index:
        return section

    for child_section in section.child_sections:
        try:
            return find_section_by_index(index, child_section)
        except KeyError:
            continue

    raise KeyError(f"Section with index {index} not found")

def get_max_section_index(section: OcrResultSection) -> int:
    max_index = section.section_index

    for child_section in section.child_sections:
        child_max_index = get_max_section_index(child_section)
        if child_max_index > max_index:
            max_index = child_max_index

    return max_index

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
            text_type=block_type
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

