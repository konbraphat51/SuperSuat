"""Figure detection backed by PP-StructureV3's layout detection model."""

import logging

from PIL.Image import Image

# imported before paddle, which otherwise shadows torch's DLLs on Windows (see the Blocker)
from ...Blocked.Blocker.PpStructure import DEFAULT_MODEL_NAME, PpStructureBlocker
from paddleocr import LayoutDetection

from .FigureDetector import FigureDetector

logger = logging.getLogger(__name__)

# The PP-DocLayout labels kept; header/footer images are logos, not figures of the content.
FIGURE_LABELS = frozenset({"image", "chart"})


class PpStructureFigureDetector(FigureDetector):
    """Finds the figures of page images with PP-StructureV3's layout model."""

    # The PaddleX predictor mixes up the results of pages predicted from several threads at once.
    MAX_PARALLEL_PAGES = 1

    def __init__(
        self,
        device: str | None = None,
        model_name: str = DEFAULT_MODEL_NAME,
        model_dir: str | None = None,
        threshold: float | None = None,
    ) -> None:
        """Loads the layout model onto `device`, or onto the best one available.

        Args:
            device: Paddle device the model runs on, e.g. "gpu" or "cpu".
            model_name: Layout model to run, from the PP-DocLayout family.
            model_dir: Local model directory to use instead of the released one.
            threshold: Lowest detection score kept; the model default if None.
        """
        self._device = device or PpStructureBlocker.default_device()
        self._detector = LayoutDetection(
            model_name=model_name,
            model_dir=model_dir,
            threshold=threshold,
            device=self._device,
        )
        logger.info(
            "PpStructureFigureDetector ready on device=%s with model=%s",
            self._device,
            model_name,
        )

    def _detect_page_figures(self, page: Image) -> list[tuple[int, int, int, int]]:
        """The boxes PP-DocLayout labels as images or charts in the page."""
        detection = self._detector.predict(PpStructureBlocker._to_bgr_array(page))[0]

        return [
            PpStructureBlocker._to_bounding_box(box["coordinate"])
            for box in detection["boxes"]
            if box["label"] in FIGURE_LABELS
        ]
