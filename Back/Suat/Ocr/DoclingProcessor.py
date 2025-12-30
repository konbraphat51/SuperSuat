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

# Configure module logger
logger = logging.getLogger(__name__)


def _parse_bool_env(env_name: str, default: bool = True) -> bool:
    """Parse a boolean from an environment variable.
    
    Args:
        env_name: The name of the environment variable.
        default: The default value if the variable is not set.
    
    Returns:
        True if the value is truthy ('true', '1', 'yes', 'on'), False otherwise.
    """
    value = os.environ.get(env_name)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")


class ElementType(str, Enum):
    """Types of document elements."""
    TEXT = "text"
    EQUATION = "equation"
    FIGURE = "figure"
    TABLE = "table"


@dataclass
class TextElement:
    """Represents a text element in the document."""
    content: str
    label: str
    reading_order: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": ElementType.TEXT.value,
            "content": self.content,
            "label": self.label,
            "reading_order": self.reading_order,
        }


@dataclass
class ImageElement:
    """Represents an image element (equation, figure, or table) in the document."""
    element_type: ElementType
    filename: str
    reading_order: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.element_type.value,
            "filename": self.filename,
            "reading_order": self.reading_order,
        }


@dataclass
class PageData:
    """Represents a page with its elements."""
    page_number: int
    elements: list[TextElement | ImageElement] = field(default_factory=list)

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


def _get_element_type_from_label(label: DocItemLabel) -> ElementType:
    """Map Docling label to ElementType."""
    if label == DocItemLabel.FORMULA:
        return ElementType.EQUATION
    elif label in [DocItemLabel.PICTURE, DocItemLabel.CHART]:
        return ElementType.FIGURE
    elif label == DocItemLabel.TABLE:
        return ElementType.TABLE
    else:
        return ElementType.TEXT


def _is_image_element(label: DocItemLabel) -> bool:
    """Check if the label represents an image element (equation, figure, table)."""
    return label in [DocItemLabel.FORMULA, DocItemLabel.PICTURE, DocItemLabel.TABLE, DocItemLabel.CHART]


def process_pdf(pdf_path: str | Path, output_dir: str | Path) -> DocumentOutput:
    """
    Process a PDF file using Docling and extract OCR data, structure data,
    and images for equations, figures, and tables.

    Args:
        pdf_path: Path to the input PDF file.
        output_dir: Directory where output files will be saved.

    Returns:
        DocumentOutput containing structured data from the PDF.
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Configure pipeline options for better extraction
    # OCR settings can be controlled via environment variable DOCLING_ENABLE_OCR
    enable_ocr = _parse_bool_env("DOCLING_ENABLE_OCR", default=True)
    
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = enable_ocr
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
    pipeline_options.images_scale = 2.0
    pipeline_options.generate_page_images = True
    pipeline_options.generate_picture_images = True
    pipeline_options.generate_table_images = True

    # Create document converter
    format_option = PdfFormatOption(
        pipeline_options=pipeline_options,
    )
    converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={
            InputFormat.PDF: format_option,
        },
    )

    # Convert the document
    result = converter.convert(str(pdf_path))
    doc = result.document

    # Initialize output structure
    output = DocumentOutput(source_pdf=pdf_path.name)

    # Track reading order globally
    reading_order = 0

    # Process document items by iterating through the document
    # Group elements by page
    page_elements: dict[int, list[TextElement | ImageElement]] = {}
    image_counter: dict[str, int] = {"equation": 0, "figure": 0, "table": 0}

    for item, level in doc.iterate_items():
        # Get page number (default to 1 if not available)
        page_num = 1
        if hasattr(item, "prov") and item.prov:
            for prov in item.prov:
                if hasattr(prov, "page_no"):
                    page_num = prov.page_no
                    break

        if page_num not in page_elements:
            page_elements[page_num] = []

        # Get the label
        label = item.label if hasattr(item, "label") else DocItemLabel.TEXT

        if _is_image_element(label):
            # Handle image elements (equations, figures, tables)
            element_type = _get_element_type_from_label(label)
            type_name = element_type.value

            # Generate filename
            image_counter[type_name] += 1
            filename = f"{type_name}_{image_counter[type_name]:03d}.png"
            filepath = output_dir / filename

            # Export image
            try:
                if isinstance(item, (PictureItem, TableItem)):
                    # Get the image from the item
                    image = item.get_image(doc)
                    if image is not None:
                        image.save(str(filepath), "PNG")
                elif hasattr(item, "image") and item.image is not None:
                    item.image.pil_image.save(str(filepath), "PNG")
            except (IOError, OSError, ValueError, AttributeError) as e:
                # If image export fails, skip but log
                logger.warning("Could not export image for %s: %s", type_name, e)
                filename = f"{type_name}_{image_counter[type_name]:03d}_missing.png"

            element = ImageElement(
                element_type=element_type,
                filename=filename,
                reading_order=reading_order,
            )
            page_elements[page_num].append(element)
        else:
            # Handle text elements
            content = ""
            if hasattr(item, "text"):
                content = item.text
            elif hasattr(item, "export_to_markdown"):
                content = item.export_to_markdown()

            if content:  # Only add non-empty text elements
                element = TextElement(
                    content=content,
                    label=label.value if hasattr(label, "value") else str(label),
                    reading_order=reading_order,
                )
                page_elements[page_num].append(element)

        reading_order += 1

    # Build output pages
    for page_num in sorted(page_elements.keys()):
        page_data = PageData(
            page_number=page_num,
            elements=page_elements[page_num],
        )
        output.pages.append(page_data)

    return output


def process_pdf_to_folder(pdf_path: str | Path) -> Path:
    """
    Process a PDF file and create an output folder with all extracted data.

    This function:
    1. Creates a folder named after the PDF (without extension)
    2. Extracts all content using Docling
    3. Exports equations, figures, and tables as PNG files
    4. Creates a JSON file with text data, image filenames, and reading order

    Args:
        pdf_path: Path to the input PDF file.

    Returns:
        Path to the output folder.
    """
    pdf_path = Path(pdf_path)

    # Create output folder named after PDF
    output_folder = pdf_path.parent / pdf_path.stem
    output_folder.mkdir(parents=True, exist_ok=True)

    # Process the PDF
    output = process_pdf(pdf_path, output_folder)

    # Save JSON output
    json_path = output_folder / "output.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output.to_dict(), f, ensure_ascii=False, indent=2)

    return output_folder


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Process PDF files using Docling to extract OCR data, "
                    "structure data, and export images for equations, figures, and tables."
    )
    parser.add_argument(
        "pdf_path",
        type=str,
        help="Path to the PDF file to process"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging based on verbosity
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    output_folder = process_pdf_to_folder(args.pdf_path)
    print(f"Output saved to: {output_folder}")


if __name__ == "__main__":
    main()
