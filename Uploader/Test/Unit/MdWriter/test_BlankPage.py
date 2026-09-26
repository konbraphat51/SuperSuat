"""Tests for telling a blank page from its image."""

from PIL import Image, ImageDraw

from OcrModule.MdWriter.Transcriber.BlankPage import BlankPageDetector, ink_ratio


def page_with_ink(ink_pixels: int) -> Image.Image:
    """A white 100x100 page with the given number of black pixels on its first rows."""
    page = Image.new("RGB", (100, 100), "white")
    draw = ImageDraw.Draw(page)
    for index in range(ink_pixels):
        draw.point((index % 100, index // 100), fill="black")
    return page


def test_a_white_page_holds_no_ink():
    assert ink_ratio(page_with_ink(0)) == 0


def test_the_ink_ratio_is_the_share_of_dark_pixels():
    assert ink_ratio(page_with_ink(250)) == 0.025


def test_light_grey_is_not_ink():
    assert ink_ratio(Image.new("RGB", (10, 10), (200, 200, 200))) == 0


def test_a_page_with_a_few_specks_is_blank():
    assert BlankPageDetector(max_ink_ratio=0.001).is_blank(page_with_ink(10))


def test_a_page_with_print_on_it_is_not_blank():
    assert not BlankPageDetector(max_ink_ratio=0.001).is_blank(page_with_ink(100))
