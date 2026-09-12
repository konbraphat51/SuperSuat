import base64
from typing import Literal
from io import BytesIO
from PIL.Image import Image
from pydantic import BaseModel, Field
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from ...OcrSchema import OcrResultBlockImage, OcrResultBlockText, OcrResultSection, OcrResultBlock, TEXT_BLOCK_TYPES


class BoundingBoxOutput(BaseModel):
    bounding_box: tuple[int, int, int, int] = Field(
        description="The bounding box of the clipped region in the image, as (x, y, width, height)."
    )


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

class LinearTools:
    def __init__(
        self,
        all_page_images: list[Image],
        ocr_entire_section: OcrResultSection,
        clipper_model: BaseChatModel,
    ) -> None:
        self.all_page_images = all_page_images
        self.ocr_entire_section = ocr_entire_section
        self.clipper_model = clipper_model
        self.current_page_number = -1  # 0-indexed

    def set_current_page(
        self,
        page_number: int,
    ) -> None:
        if page_number < 0 or page_number >= len(self.all_page_images):
            raise ValueError(f"Invalid page number. The page number must be between 0 and {len(self.all_page_images) - 1}")

        self.current_page_number = page_number

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
        mark_existing_page(self.ocr_entire_section, block_index, self.current_page_number)
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
        mark_existing_page(self.ocr_entire_section, new_block_index, self.current_page_number)

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
        mark_existing_page(self.ocr_entire_section, new_block_index, self.current_page_number)

        return f"New image block added to section {section_index} with block index {new_block_index}. The caption is: \n{caption}"

    def add_section(
        self,
        parent_section_index: int,
    ) -> str:
        try:
            parent_section = find_section_by_index(parent_section_index, self.ocr_entire_section)
        except KeyError:
            return f"ERROR: Section with index {parent_section_index} not found"

        new_section_index = get_max_block_index(self.ocr_entire_section) + 1
        new_section = OcrResultSection(
            section_content=[],
            child_sections=[],
            section_index=new_section_index
        )
        parent_section.section_content.append(new_section)
        mark_existing_page(self.ocr_entire_section, new_section_index, self.current_page_number)

        return f"New section added to parent section {parent_section_index} with section index {new_section_index}"

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

    def clip_image(
        self,
        order: str,
    ) -> str:
        if self.current_page_number == -1:
            return "ERROR: Current page is not set. Please set the current page first."

        img = self.all_page_images[self.current_page_number]
        img_b64 = pil_to_base64(img)

        structured_clipper_model = self.clipper_model.with_structured_output(BoundingBoxOutput)
        result: BoundingBoxOutput = structured_clipper_model.invoke([
            HumanMessage(content=[
                {"type": "text", "text": order},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                },
            ])
        ])

        return f"Clipped bounding box: {result.bounding_box}"
