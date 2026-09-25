"""Figure detection backed by the DocLayout-YOLO layout detector."""

import logging

from doclayout_yolo import YOLOv10
from PIL.Image import Image

from ...Blocked.Blocker.DocLayoutYolo import (
    DEFAULT_CONFIDENCE,
    DEFAULT_IMAGE_SIZE,
    DEFAULT_IOU,
    DocLayoutYoloBlocker,
)
from .FigureDetector import FigureDetector

logger = logging.getLogger(__name__)

# The DocStructBench classes kept; captions are left to the model, which writes them as alt text.
FIGURE_CLASS_NAMES = frozenset({"figure"})


class DocLayoutYoloFigureDetector(FigureDetector):
    """Finds the figures of page images with DocLayout-YOLO.

    Runs the same released checkpoint as DocLayoutYoloBlocker, keeping only
    the regions it classes as figures."""

    def __init__(
        self,
        device: str | None = None,
        weight_path: str | None = None,
        image_size: int = DEFAULT_IMAGE_SIZE,
        confidence: float = DEFAULT_CONFIDENCE,
        iou: float = DEFAULT_IOU,
    ) -> None:
        """Loads the detector onto `device`, or onto the best one available.

        Args:
            device: Torch device the model runs on, e.g. "cuda" or "cpu".
            weight_path: Local checkpoint to use instead of the released one.
            image_size: Side the page is resized to before detection.
            confidence: Lowest detection score kept.
            iou: IoU threshold of the non-maximum suppression.
        """
        self._device = device or DocLayoutYoloBlocker.default_device()
        self._image_size = image_size
        self._confidence = confidence
        self._iou = iou
        self._model = YOLOv10(weight_path or DocLayoutYoloBlocker.default_weight_path())
        logger.info("DocLayoutYoloFigureDetector ready on device=%s", self._device)

    def _detect_page_figures(self, page: Image) -> list[tuple[int, int, int, int]]:
        """The boxes DocLayout-YOLO classes as figures in the page."""
        prediction = self._model.predict(
            page.convert("RGB"),
            imgsz=self._image_size,
            conf=self._confidence,
            iou=self._iou,
            device=self._device,
            verbose=False,
        )[0]

        boxes = prediction.boxes.xyxy.cpu().numpy()
        classes = prediction.boxes.cls.cpu().numpy()

        return [
            DocLayoutYoloBlocker._to_bounding_box(box)
            for box, class_index in zip(boxes, classes)
            if prediction.names[int(class_index)] in FIGURE_CLASS_NAMES
        ]
