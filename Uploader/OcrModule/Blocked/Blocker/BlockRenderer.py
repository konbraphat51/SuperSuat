"""Draws a BlockerResult's boxes and IDs onto page images, for visual debugging."""

from PIL import ImageDraw, ImageFont
from PIL.Image import Image

from ..Schema import Block, BlockerResult, BlockType

# Outline color per block type, so the drawn boxes double as a type legend.
BLOCK_TYPE_COLORS = {
    BlockType.TEXT: "blue",
    BlockType.MATH: "purple",
    BlockType.IMAGE: "green",
    BlockType.TABLE: "orange",
}

DEFAULT_OUTLINE_WIDTH = 2

# Large enough to read at a glance on a 200 DPI page render.
DEFAULT_FONT_SIZE = 28


class BlockRenderer:
    """Renders a BlockerResult's boxes and IDs onto copies of the page images."""

    def __init__(self, font_size: int = DEFAULT_FONT_SIZE) -> None:
        """Args:
        font_size: Point size the block ID labels are drawn at.
        """
        self._font = ImageFont.load_default(size=font_size)

    def render(
        self,
        pages: list[Image],
        blocker_result: BlockerResult,
    ) -> list[Image]:
        """Returns one annotated copy of each page, boxes and IDs drawn on top.

        The input pages are left untouched.
        """
        rendered = [page.convert("RGB") for page in pages]

        for block in blocker_result.blocks:
            self._draw_block(rendered[block.page_number], block)

        return rendered

    def _draw_block(self, page: Image, block: Block) -> None:
        """Draws one block's outline and ID number onto the page, in place."""
        x, y, width, height = block.bounding_box
        color = BLOCK_TYPE_COLORS.get(block.block_type, "red")

        draw = ImageDraw.Draw(page)
        draw.rectangle(
            (x, y, x + width, y + height), outline=color, width=DEFAULT_OUTLINE_WIDTH
        )

        # A filled backing box keeps the ID legible over busy page content.
        label = str(block.block_id)
        label_box = draw.textbbox((x, y), label, font=self._font)
        draw.rectangle(label_box, fill=color)
        draw.text((x, y), label, fill="white", font=self._font)
