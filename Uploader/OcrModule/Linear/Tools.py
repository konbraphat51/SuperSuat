from langchain_core.language_models import BaseChatModel
from ..OcrSchema import OcrResultSection
from ..LlmHelper import ImageBase64, ImageMessageBuilder
from .Clipper import clip_image_with_agent


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


def recompute_existing_pages(section: OcrResultSection) -> list[int]:
    """Recomputes existing_pages of `section` and of every section under it as the union of the pages of its contents, and returns the section's pages. A section with no contents keeps the pages it already has, since it has nothing to derive them from."""
    pages: set[int] = set()

    for block in section.section_content:
        if isinstance(block, OcrResultSection):
            pages.update(recompute_existing_pages(block))
        else:
            pages.update(block.existing_pages)

    if section.section_content:
        section.existing_pages = sorted(pages)

    return section.existing_pages


class LinearTools:
    def __init__(
        self,
        all_pages: list[ImageBase64],
        ocr_entire_section: OcrResultSection,
        clipper_model: BaseChatModel,
        image_message_builder: ImageMessageBuilder,
    ) -> None:
        self.all_pages = all_pages
        self.ocr_entire_section = ocr_entire_section
        self.clipper_model = clipper_model
        self.image_message_builder = image_message_builder
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

        return self.image_message_builder(
            f"this is the image of page {page_number}",
            self.all_pages[page_number].b64,
        )

    def clip_image(
        self,
        order: str,
    ) -> str:
        """Clip a region of the current page's image according to `order`, and return its bounding box."""
        if self.current_page_number == -1:
            return "ERROR: Current page is not set. Please set the current page first."

        current_page = self.all_pages[self.current_page_number]

        try:
            result = clip_image_with_agent(
                self.clipper_model,
                order,
                current_page.b64,
                current_page.size,
                self.image_message_builder,
            )
        except Exception as error:
            return f"ERROR: The clipping agent failed: {error}"

        return f"Clipped bounding box: {result.bounding_box}"
