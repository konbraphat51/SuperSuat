"""Draws a Blocker's boxes and IDs onto page images, for the Classifier and for debugging."""

from collections.abc import Sequence

from PIL import ImageDraw, ImageFont
from PIL.Image import Image

from ..Schema import Block, BlockerResult, BoxedBlock

# One color for every box: the Blocker no longer guesses what a block is, so
# there is nothing for a color to say.
OUTLINE_COLOR = "red"

DEFAULT_OUTLINE_WIDTH = 2

# Large enough to read at a glance on a 200 DPI page render.
DEFAULT_FONT_SIZE = 28


class BlockRenderer:
    """Renders blocks' boxes and IDs onto copies of the page images."""

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

        Every page is held in memory at once, so this is for writing the pages
        out; a stage reading one page at a time uses `render_page`.
        """
        blocks_by_page: dict[int, list[Block]] = {}
        for block in blocker_result.blocks:
            blocks_by_page.setdefault(block.page_index, []).append(block)

        return [
            self.render_page(page, blocks_by_page.get(page_index, []))
            for page_index, page in enumerate(pages)
        ]

    def render_page(
        self,
        page: Image,
        blocks: Sequence[BoxedBlock],
    ) -> Image:
        """Returns an annotated copy of one page, its blocks drawn on top.

        The input page is left untouched.
        """
        rendered = page.convert("RGB")

        for block in blocks:
            self._draw_block(rendered, block)

        return rendered

    def _draw_block(self, page: Image, block: BoxedBlock) -> None:
        """Draws one block's outline and ID number onto the page, in place."""
        x, y, width, height = block.bounding_box

        draw = ImageDraw.Draw(page)
        draw.rectangle(
            (x, y, x + width, y + height),
            outline=OUTLINE_COLOR,
            width=DEFAULT_OUTLINE_WIDTH,
        )

        # A filled backing box keeps the ID legible over busy page content.
        label = str(block.block_id)
        label_box = draw.textbbox((x, y), label, font=self._font)
        draw.rectangle(label_box, fill=OUTLINE_COLOR)
        draw.text((x, y), label, fill="white", font=self._font)
