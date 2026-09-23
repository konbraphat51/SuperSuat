"""The tools the OCR agent can call while reading a page."""

from langchain_core.language_models import BaseChatModel
from ..OcrSchema import OcrResultSection
from ..LlmHelper import ImageBase64, build_image_message
from .Clipper import clip_image_with_agent


def find_section_by_index(
    index: int,
    section: OcrResultSection,
) -> OcrResultSection:
    """The section with `index`, searching `section` and everything under it."""
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
    """Every section in the tree, `section` itself first."""
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
    """The tools bound to the OCR agent, over one document's page images."""

    def __init__(
        self,
        all_pages: list[ImageBase64],
        ocr_entire_section: OcrResultSection,
        clipper_model: BaseChatModel,
    ) -> None:
        self.all_pages = all_pages
        self.ocr_entire_section = ocr_entire_section
        self.clipper_model = clipper_model
        self.current_page_index = -1  # 0-indexed

    def set_current_page(
        self,
        page_index: int,
    ) -> str:
        """Set the page currently being processed, 0-indexed."""
        if page_index < 0 or page_index >= len(self.all_pages):
            return f"ERROR: Invalid page number. The page number must be between 1 and {len(self.all_pages)}"

        self.current_page_index = page_index
        return f"Current page set to {page_index + 1}"

    def get_page_image(self, page_number: int):
        """Get the image of the specified page number. Pages are numbered from 1."""
        # the agent counts pages from 1, everything here counts from 0
        return self.page_image_message(page_number - 1)

    def page_image_message(self, page_index: int):
        """The image of the page with `page_index`, as message content."""
        if page_index < 0 or page_index >= len(self.all_pages):
            return f"ERROR: Invalid page number. The page number must be between 1 and {len(self.all_pages)}"

        return build_image_message(
            f"this is the image of page {page_index + 1}",
            self.all_pages[page_index].b64,
        )

    def clip_image(
        self,
        order: str,
    ) -> str:
        """Clip a region of the current page's image according to `order`, and return its bounding box."""
        if self.current_page_index == -1:
            return "ERROR: Current page is not set. Please set the current page first."

        current_page = self.all_pages[self.current_page_index]

        # a clipper failure is reported to the agent like any other tool
        # error, rather than escaping and aborting the whole document
        try:
            result = clip_image_with_agent(
                self.clipper_model,
                order,
                current_page.b64,
                current_page.size,
            )
        except Exception as error:
            return f"ERROR: The clipping agent failed: {error}"

        return f"Clipped bounding box: {result.bounding_box}"
