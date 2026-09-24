"""Tests for the figures of every page being numbered across the document."""

from PIL import Image
from PIL.Image import Image as PilImage

from OcrModule.Blocked.Blocker.BlockRenderer import BlockRenderer
from OcrModule.LinearMD.FigureDetector import FigureDetector


class FakeFigureDetector(FigureDetector):
    """Finds the boxes it was given for each page, keyed by the page's width."""

    def __init__(self, boxes_by_width: dict[int, list[tuple[int, int, int, int]]]):
        self._boxes_by_width = boxes_by_width

    def _detect_page_figures(self, page: PilImage) -> list[tuple[int, int, int, int]]:
        return self._boxes_by_width[page.width]


def page(width: int) -> PilImage:
    return Image.new("RGB", (width, 100), "white")


def test_figures_are_numbered_in_page_order_then_top_to_bottom():
    detector = FakeFigureDetector(
        {
            10: [(0, 50, 5, 5), (0, 10, 5, 5)],
            11: [],
            12: [(5, 0, 5, 5), (0, 0, 5, 5)],
        }
    )

    figures = detector.detect([page(10), page(11), page(12)])

    assert [(f.block_id, f.page_index, f.bounding_box) for f in figures] == [
        (0, 0, (0, 10, 5, 5)),
        (1, 0, (0, 50, 5, 5)),
        (2, 2, (0, 0, 5, 5)),
        (3, 2, (5, 0, 5, 5)),
    ]


def test_a_document_without_figures_gives_none():
    assert FakeFigureDetector({10: []}).detect([page(10)]) == []


def test_the_figures_can_be_drawn_by_the_block_renderer():
    detector = FakeFigureDetector({40: [(0, 0, 30, 30)]})
    blank = page(40)

    rendered = BlockRenderer(font_size=8).render_page(blank, detector.detect([blank]))

    assert rendered.getpixel((0, 29)) != (255, 255, 255)
    assert blank.getpixel((0, 29)) == (255, 255, 255)
