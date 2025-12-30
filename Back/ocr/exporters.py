"""Exporters for images and output data."""

from __future__ import annotations
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from docling_core.types.doc import PictureItem, TableItem

from .models import DocumentOutput, ElementType

logger = logging.getLogger(__name__)


@dataclass
class ExportResult:
    """Result of an image export operation."""
    filename: str
    success: bool


class ImageExporter:
    """Handles exporting images from document items."""
    
    def __init__(self, output_dir: Path):
        self._output_dir = output_dir
        self._counters: dict[str, int] = {"equation": 0, "figure": 0, "table": 0}

    def export(self, item: Any, doc: Any, element_type: ElementType) -> ExportResult:
        """Export image and return result with filename and success status."""
        type_name = element_type.value
        self._counters[type_name] += 1
        filename = f"{type_name}_{self._counters[type_name]:03d}.png"
        filepath = self._output_dir / filename

        try:
            self._save_image(item, doc, filepath)
            return ExportResult(filename=filename, success=True)
        except (IOError, OSError, ValueError, AttributeError) as e:
            logger.warning("Could not export image for %s: %s", type_name, e)
            return ExportResult(filename=filename, success=False)

    def _save_image(self, item: Any, doc: Any, filepath: Path) -> None:
        """Save image to file."""
        if isinstance(item, (PictureItem, TableItem)):
            image = item.get_image(doc)
            if image is not None:
                image.save(str(filepath), "PNG")
        elif hasattr(item, "image") and item.image is not None:
            item.image.pil_image.save(str(filepath), "PNG")


class OutputWriter:
    """Writes processing output to files."""
    
    @staticmethod
    def write_json(output: DocumentOutput, output_path: Path) -> None:
        """Write document output to JSON file."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output.to_dict(), f, ensure_ascii=False, indent=2)
