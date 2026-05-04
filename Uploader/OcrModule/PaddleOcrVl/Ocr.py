from __future__ import annotations

import io
import json
import os
import re
from pathlib import Path

# Redirect PaddleX / PaddlePaddle model cache to the sibling `cache/` directory
# before paddlex is imported so the paths take effect from the start.
_CACHE_DIR = Path(__file__).parent / "cache"
_CACHE_DIR.mkdir(exist_ok=True)
os.environ.setdefault("PADDLE_HOME", str(_CACHE_DIR / "paddle"))
os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(_CACHE_DIR / "paddlex"))

from PIL import Image  # noqa: E402
from paddlex import create_pipeline  # noqa: E402

from ..Ocr import (
    Ocr,
    OcrResult,
    OcrResultBlock,
    OcrResultBlockEquation,
    OcrResultBlockFooter,
    OcrResultBlockImage,
    OcrResultBlockSection,
    OcrResultBlockTable,
    OcrResultBlockText,
)

# PaddleOCR-VL 1.5 layout element type -> our block type
_LAYOUT_TYPE_MAP: dict[str, str] = {
    "title": "section",
    "section_title": "section",
    "heading": "section",
    "text": "text",
    "paragraph": "text",
    "figure": "image",
    "figure_caption": "image",
    "table": "table",
    "table_caption": "table",
    "equation": "equation",
    "formula": "equation",
    "footer": "footer",
    "footnote": "footer",
    "header": "footer",
}

_HEADING_LEVEL_RE = re.compile(r"h(\d)", re.IGNORECASE)


def _heading_level(layout_type: str) -> int:
    m = _HEADING_LEVEL_RE.search(layout_type)
    return int(m.group(1)) if m else 1


def _pil_from_bytes(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data)).convert("RGB")


def _parse_element(elem: dict) -> OcrResultBlock | None:
    raw_type: str = elem.get("type", "text").lower()
    block_type = _LAYOUT_TYPE_MAP.get(raw_type, "text")

    text: str = elem.get("text", "") or ""
    caption: str = elem.get("caption", "") or ""

    if block_type == "section":
        block = OcrResultBlockSection(block_type="section")
        block.text = text
        block.level = _heading_level(raw_type)
        return block

    if block_type == "text":
        block = OcrResultBlockText(block_type="text")
        block.text = text
        return block

    if block_type == "image":
        block = OcrResultBlockImage(block_type="image")
        block.image_data = elem.get("image_bytes", b"")
        block.caption = caption or text
        return block

    if block_type == "table":
        block = OcrResultBlockTable(block_type="table")
        block.text = elem.get("markdown", text)
        block.caption = caption
        return block

    if block_type == "equation":
        block = OcrResultBlockEquation(block_type="equation")
        block.text = elem.get("latex", text)
        block.caption = caption
        return block

    if block_type == "footer":
        block = OcrResultBlockFooter(block_type="footer")
        block.text = text
        return block

    # fallback
    block = OcrResultBlockText(block_type="text")
    block.text = text
    return block


def _extract_elements(page_result) -> list[dict]:
    """Normalise the paddlex pipeline output into a flat list of element dicts."""
    if hasattr(page_result, "to_json"):
        raw = page_result.to_json()
        data = json.loads(raw) if isinstance(raw, str) else raw
    elif hasattr(page_result, "json"):
        data = page_result.json
    elif isinstance(page_result, dict):
        data = page_result
    else:
        return []

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("layout_elements", "elements", "blocks", "result"):
            if key in data and isinstance(data[key], list):
                return data[key]
    return []


class PaddleOcrVlOcr(Ocr):
    """OCR using PaddleOCR-VL 1.5 (PP-DocBee2 / StructureV3 via paddlex pipeline)."""

    def __init__(self) -> None:
        # "doc_understanding" bundles layout analysis + VLM-based reading
        self._pipeline = create_pipeline(pipeline="doc_understanding")

    _QUERY = (
        "Recognize all content in the document image and output in markdown format."
    )

    def ocr(self, image_data: list[bytes]) -> OcrResult:
        images = [_pil_from_bytes(d) for d in image_data]

        blocks: list[OcrResultBlock] = []
        for image in images:
            for page_result in self._pipeline.predict(
                {"image": image, "query": self._QUERY}
            ):
                for elem in _extract_elements(page_result):
                    block = _parse_element(elem)
                    if block is not None:
                        blocks.append(block)

        result = OcrResult()
        result.blocks = blocks
        return result
