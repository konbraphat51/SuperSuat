"""Figure detection backed by yomitoku's layout analysis models."""

import logging
from typing import Any

from PIL.Image import Image
from yomitoku import LayoutAnalyzer

from ...Blocked.Blocker.Yomitoku import YomitokuBlocker
from .FigureDetector import FigureDetector

logger = logging.getLogger(__name__)


class YomitokuFigureDetector(FigureDetector):
    """Finds the figures of page images with yomitoku's layout analyzer.

    Only the analyzer's figures are kept: its paragraphs and tables are
    written out by the model from the page."""

    def __init__(
        self,
        device: str | None = None,
        configs: dict[str, Any] | None = None,
    ) -> None:
        """Loads the layout models onto `device`, or onto the best one available.

        Args:
            device: Torch device the models run on, e.g. "cuda" or "cpu".
            configs: Per-model yomitoku overrides, keyed by model name.
        """
        self._device = device or YomitokuBlocker.default_device()
        self._analyzer = LayoutAnalyzer(
            configs=configs or {},
            device=self._device,
            visualize=False,
        )
        logger.info("YomitokuFigureDetector ready on device=%s", self._device)

    def _detect_page_figures(self, page: Image) -> list[tuple[int, int, int, int]]:
        """The boxes yomitoku finds figures in, in the page."""
        layout, _ = self._analyzer(YomitokuBlocker._to_bgr_array(page))

        return [
            YomitokuBlocker._to_bounding_box(figure.box) for figure in layout.figures
        ]
