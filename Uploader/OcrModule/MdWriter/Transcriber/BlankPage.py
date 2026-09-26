"""Telling a blank page from its image alone, so no model is asked to write it."""

from PIL.Image import Image

# Grey level below which a pixel counts as ink, out of 255.
INK_THRESHOLD = 128

# Share of ink pixels at or below which a page is blank: a line of print is
# well above it, while scanner specks and a lone page number stay under it.
DEFAULT_MAX_INK_RATIO = 0.0001


class BlankPageDetector:
    """Says whether a page image holds next to no ink, and so nothing to transcribe."""

    def __init__(self, max_ink_ratio: float = DEFAULT_MAX_INK_RATIO) -> None:
        """
        Args:
            max_ink_ratio: The share of ink pixels at or below which a page is blank.
        """
        self.max_ink_ratio = max_ink_ratio

    def is_blank(self, page: Image) -> bool:
        """Whether the page holds no more ink than max_ink_ratio allows."""
        return ink_ratio(page) <= self.max_ink_ratio


def ink_ratio(page: Image) -> float:
    """The share of the page's pixels dark enough to be ink."""
    histogram = page.convert("L").histogram()
    return sum(histogram[:INK_THRESHOLD]) / sum(histogram)
