"""
Docling PDF Processor module.

This module provides functionality to process PDFs using Docling,
extracting OCR data, structure data, and exporting detected
equations, figures, and tables as PNG images.

Requirements:
- Docling requires internet access on first run to download model weights
- Models are cached locally after first download
"""

from __future__ import annotations
import argparse
import logging
import os
import json
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field
from enum import Enum

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableFormerMode,
)
from docling_core.types.doc import (
    DocItemLabel,
    PictureItem,
    TableItem,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class ProcessorConfig:
    """Configuration for PDF processing."""
    enable_ocr: bool = True
    table_mode: TableFormerMode = TableFormerMode.ACCURATE
    images_scale: float = 2.0

    @classmethod
    def from_env(cls) -> ProcessorConfig:
        """Create configuration from environment variables."""
        enable_ocr = os.environ.get("DOCLING_ENABLE_OCR", "true").lower() in ("true", "1", "yes", "on")
        return cls(enable_ocr=enable_ocr)


# =============================================================================
# Data Models
# =============================================================================

class ElementType(str, Enum):
    """Types of document elements."""
    TEXT = "text"
    EQUATION = "equation"
    FIGURE = "figure"
    TABLE = "table"


@dataclass
class TextElement:
    """Represents a text element in the document."""
    reading_order: int
    content: str
    label: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": ElementType.TEXT.value,
            "content": self.content,
            "label": self.label,
            "reading_order": self.reading_order,
        }


@dataclass
class ImageElement:
    """Represents an image element (equation, figure, or table)."""
    reading_order: int
    element_type: ElementType
    filename: str
    exported: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.element_type.value,
            "filename": self.filename,
            "reading_order": self.reading_order,
            "exported": self.exported,
        }


# Type alias for document elements
DocumentElement = TextElement | ImageElement


@dataclass
class PageData:
    """Represents a page with its elements."""
    page_number: int
    elements: list[DocumentElement] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_number": self.page_number,
            "elements": [elem.to_dict() for elem in self.elements],
        }


@dataclass
class DocumentOutput:
    """Output data structure for the processed document."""
    source_pdf: str
    pages: list[PageData] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_pdf": self.source_pdf,
            "pages": [page.to_dict() for page in self.pages],
        }


# =============================================================================
# Element Type Mapping
# =============================================================================

class LabelMapper:
    """Maps Docling labels to element types."""
    
    IMAGE_LABELS = frozenset([DocItemLabel.FORMULA, DocItemLabel.PICTURE, DocItemLabel.TABLE, DocItemLabel.CHART])
    
    LABEL_TO_TYPE = {
        DocItemLabel.FORMULA: ElementType.EQUATION,
        DocItemLabel.PICTURE: ElementType.FIGURE,
        DocItemLabel.CHART: ElementType.FIGURE,
        DocItemLabel.TABLE: ElementType.TABLE,
    }

    @classmethod
    def is_image_element(cls, label: DocItemLabel) -> bool:
        """Check if label represents an image element."""
        return label in cls.IMAGE_LABELS

    @classmethod
    def get_element_type(cls, label: DocItemLabel) -> ElementType:
        """Get ElementType from DocItemLabel."""
        return cls.LABEL_TO_TYPE.get(label, ElementType.TEXT)


# =============================================================================
# Image Exporter
# =============================================================================

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


# =============================================================================
# Document Converter Factory
# =============================================================================

class ConverterFactory:
    """Creates configured DocumentConverter instances."""
    
    @staticmethod
    def create(config: ProcessorConfig) -> DocumentConverter:
        """Create a DocumentConverter with the given configuration."""
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = config.enable_ocr
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.mode = config.table_mode
        pipeline_options.images_scale = config.images_scale
        pipeline_options.generate_page_images = True
        pipeline_options.generate_picture_images = True
        pipeline_options.generate_table_images = True

        format_option = PdfFormatOption(pipeline_options=pipeline_options)
        return DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={InputFormat.PDF: format_option},
        )


# =============================================================================
# Document Item Processor
# =============================================================================

class ItemProcessor:
    """Processes individual document items."""
    
    def __init__(self, image_exporter: ImageExporter, doc: Any):
        self._image_exporter = image_exporter
        self._doc = doc

    def process(self, item: Any, reading_order: int) -> DocumentElement | None:
        """Process a document item and return the appropriate element."""
        label = getattr(item, "label", DocItemLabel.TEXT)
        
        if LabelMapper.is_image_element(label):
            return self._create_image_element(item, label, reading_order)
        return self._create_text_element(item, label, reading_order)

    def _create_image_element(self, item: Any, label: DocItemLabel, reading_order: int) -> ImageElement:
        """Create an ImageElement from a document item."""
        element_type = LabelMapper.get_element_type(label)
        result = self._image_exporter.export(item, self._doc, element_type)
        return ImageElement(
            reading_order=reading_order,
            element_type=element_type,
            filename=result.filename,
            exported=result.success,
        )

    def _create_text_element(self, item: Any, label: DocItemLabel, reading_order: int) -> TextElement | None:
        """Create a TextElement from a document item."""
        content = self._extract_text_content(item)
        if not content:
            return None
        label_str = label.value if hasattr(label, "value") else str(label)
        return TextElement(reading_order=reading_order, content=content, label=label_str)

    @staticmethod
    def _extract_text_content(item: Any) -> str:
        """Extract text content from a document item."""
        if hasattr(item, "text") and item.text:
            return item.text
        if hasattr(item, "export_to_markdown"):
            return item.export_to_markdown()
        return ""

    @staticmethod
    def get_page_number(item: Any) -> int:
        """Extract page number from document item."""
        if hasattr(item, "prov") and item.prov:
            for prov in item.prov:
                if hasattr(prov, "page_no"):
                    return prov.page_no
        return 1


# =============================================================================
# Main Processor
# =============================================================================

class DoclingProcessor:
    """Main processor for PDF documents using Docling."""
    
    def __init__(self, config: ProcessorConfig | None = None):
        self._config = config or ProcessorConfig.from_env()
        self._converter = ConverterFactory.create(self._config)

    def process(self, pdf_path: Path, output_dir: Path) -> DocumentOutput:
        """Process a PDF file and extract structured data."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        result = self._converter.convert(str(pdf_path))
        doc = result.document
        
        image_exporter = ImageExporter(output_dir)
        item_processor = ItemProcessor(image_exporter, doc)
        
        page_elements: dict[int, list[DocumentElement]] = {}
        reading_order = 0

        for item, _ in doc.iterate_items():
            page_num = ItemProcessor.get_page_number(item)
            if page_num not in page_elements:
                page_elements[page_num] = []

            element = item_processor.process(item, reading_order)
            if element:
                page_elements[page_num].append(element)
            reading_order += 1

        output = DocumentOutput(source_pdf=pdf_path.name)
        for page_num in sorted(page_elements.keys()):
            output.pages.append(PageData(page_number=page_num, elements=page_elements[page_num]))
        
        return output


# =============================================================================
# Output Writer
# =============================================================================

class OutputWriter:
    """Writes processing output to files."""
    
    @staticmethod
    def write_json(output: DocumentOutput, output_path: Path) -> None:
        """Write document output to JSON file."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output.to_dict(), f, ensure_ascii=False, indent=2)


# =============================================================================
# Public API
# =============================================================================

def process_pdf(pdf_path: str | Path, output_dir: str | Path) -> DocumentOutput:
    """
    Process a PDF file using Docling.

    Args:
        pdf_path: Path to the input PDF file.
        output_dir: Directory where output files will be saved.

    Returns:
        DocumentOutput containing structured data from the PDF.
    """
    processor = DoclingProcessor()
    return processor.process(Path(pdf_path), Path(output_dir))


def process_pdf_to_folder(pdf_path: str | Path) -> Path:
    """
    Process a PDF file and create an output folder with all extracted data.

    Args:
        pdf_path: Path to the input PDF file.

    Returns:
        Path to the output folder.
    """
    pdf_path = Path(pdf_path)
    output_folder = pdf_path.parent / pdf_path.stem
    
    output = process_pdf(pdf_path, output_folder)
    OutputWriter.write_json(output, output_folder / "output.json")
    
    return output_folder


def main() -> None:
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Process PDF files using Docling to extract OCR data, "
                    "structure data, and export images for equations, figures, and tables."
    )
    parser.add_argument("pdf_path", type=str, help="Path to the PDF file to process")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    output_folder = process_pdf_to_folder(args.pdf_path)
    print(f"Output saved to: {output_folder}")


if __name__ == "__main__":
    main()
