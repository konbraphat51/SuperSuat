"""Block detection backed by the DocLayout-YOLO layout detector."""

import logging
from collections.abc import Sequence

import numpy as np
import torch
from doclayout_yolo import YOLOv10
from huggingface_hub import hf_hub_download
from PIL.Image import Image

from .Blocker import Blocker
from ..Schema import BlockType

logger = logging.getLogger(__name__)

# DocStructBench weights: the variant trained on mixed real-world documents,
# which is the closest match to the papers this pipeline reads.
DEFAULT_REPOSITORY = "juliozhao/DocLayout-YOLO-DocStructBench"
DEFAULT_WEIGHT_FILE = "doclayout_yolo_docstructbench_imgsz1024.pt"

# The resolution the released weights were trained at.
DEFAULT_IMAGE_SIZE = 1024

# Detections below this score are dropped, as in the model's own demo.
DEFAULT_CONFIDENCE = 0.2

# IoU threshold of the non-maximum suppression applied to the raw detections.
DEFAULT_IOU = 0.45

# The ten DocStructBench classes, keyed by the name the checkpoint carries.
# Captions and `abandon` (running heads, footers, page numbers) are prose, so
# they stay TEXT and step 3 decides what to do with them.
CLASS_BLOCK_TYPES = {
    "title": BlockType.TEXT,
    "plain text": BlockType.TEXT,
    "abandon": BlockType.TEXT,
    "figure": BlockType.IMAGE,
    "figure_caption": BlockType.TEXT,
    "table": BlockType.TABLE,
    "table_caption": BlockType.TEXT,
    "table_footnote": BlockType.TEXT,
    "isolate_formula": BlockType.MATH,
    "formula_caption": BlockType.TEXT,
}


class DocLayoutYoloBlocker(Blocker):
    """Splits page images into blocks with DocLayout-YOLO.

    A single-shot detector: one forward pass per page gives every region and
    its class, so unlike the multi-model analyzers it needs no second stage.
    The text of each block is read later, by the OCR step."""

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
        self._device = device or self.default_device()
        self._image_size = image_size
        self._confidence = confidence
        self._iou = iou
        self._model = YOLOv10(weight_path or self.default_weight_path())
        logger.info("DocLayoutYoloBlocker ready on device=%s", self._device)

    @staticmethod
    def default_device() -> str:
        """ "cuda" whenever this machine can run the model on the GPU."""
        return "cuda" if torch.cuda.is_available() else "cpu"

    @staticmethod
    def default_weight_path() -> str:
        """The released DocStructBench checkpoint, downloaded once and cached."""
        return hf_hub_download(DEFAULT_REPOSITORY, DEFAULT_WEIGHT_FILE)

    def _detect_page(
        self, page: Image
    ) -> list[tuple[BlockType, tuple[int, int, int, int]]]:
        """The (block type, bounding box) pairs DocLayout-YOLO detects in the page."""
        prediction = self._model.predict(
            page.convert("RGB"),
            imgsz=self._image_size,
            conf=self._confidence,
            iou=self._iou,
            device=self._device,
            verbose=False,
        )[0]

        names = prediction.names
        boxes = prediction.boxes.xyxy.cpu().numpy()
        classes = prediction.boxes.cls.cpu().numpy().astype(int)

        return [
            (self._class_block_type(names[class_id]), self._to_bounding_box(box))
            for box, class_id in zip(boxes, classes)
        ]

    @staticmethod
    def _class_block_type(class_name: str) -> BlockType:
        """The BlockType a DocStructBench class maps to, defaulting to TEXT."""
        return CLASS_BLOCK_TYPES.get(class_name, BlockType.TEXT)

    @staticmethod
    def _to_bounding_box(
        box: Sequence[float] | np.ndarray,
    ) -> tuple[int, int, int, int]:
        """A YOLO [x1, y1, x2, y2] box as Block's (x, y, width, height)."""
        x1, y1, x2, y2 = (int(round(float(value))) for value in box)
        return (x1, y1, x2 - x1, y2 - y1)
