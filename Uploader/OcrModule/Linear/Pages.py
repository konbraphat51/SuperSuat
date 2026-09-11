import io
from typing import Any

from PIL.Image import Image


class PageImages:
    """The page images of the document the OCR agent is reading."""

    def __init__(self, images: list[Image]) -> None:
        self.images = images

    def load(self, images: list[Image]) -> None:
        """Replace the pages in place, so that the holders of this object see them."""
        self.images = images

    def __len__(self) -> int:
        return len(self.images)

    def resolve(self, page_index: Any) -> int:
        """Validate a 0-indexed page number given by the agent."""
        page_index = int(page_index)

        if not 0 <= page_index < len(self.images):
            raise ValueError(
                f"the page {page_index} does not exist: "
                f"the document has {len(self.images)} pages (0-indexed)."
            )

        return page_index

    def get(self, page_index: Any) -> Image:
        return self.images[self.resolve(page_index)]

    def clip(
        self,
        page_index: Any,
        bounding_box: dict[str, int] | None,
    ) -> bytes:
        """PNG data of the given area of the page. The whole page if no box is given."""
        page = self.get(page_index)

        if bounding_box is not None:
            left = max(0, int(bounding_box["x"]))
            top = max(0, int(bounding_box["y"]))
            right = min(page.width, left + int(bounding_box["width"]))
            bottom = min(page.height, top + int(bounding_box["height"]))
            if left >= right or top >= bottom:
                raise ValueError("the bounding box does not overlap the page.")
            page = page.crop((left, top, right, bottom))

        buffer = io.BytesIO()
        page.save(buffer, format="PNG")
        return buffer.getvalue()
