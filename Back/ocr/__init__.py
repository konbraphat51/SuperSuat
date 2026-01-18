"""
OCR module for PDF processing using Docling.

This module provides functionality to process PDFs using Docling,
extracting OCR data, structure data, and exporting detected
equations, figures, and tables as PNG images.

Requirements:
- Docling requires internet access on first run to download model weights
- Models are cached locally after first download
- For GPU acceleration, set DOCLING_ACCELERATOR=cuda (NVIDIA) or DOCLING_ACCELERATOR=mps (Apple Silicon)
"""

from pathlib import Path

from .config import ProcessorConfig, AcceleratorDevice
from .models import (
    DocumentElement,
    DocumentOutput,
    ElementType,
    HierarchyNode,
    ImageElement,
    PageData,
    TextElement,
)
from .exporters import OutputWriter
from .processor import DoclingProcessor

__all__ = [
    "AcceleratorDevice",
    "DocumentElement",
    "DocumentOutput",
    "DoclingProcessor",
    "ElementType",
    "HierarchyNode",
    "ImageElement",
    "OutputWriter",
    "PageData",
    "ProcessorConfig",
    "TextElement",
    "process_pdf",
    "process_pdf_to_folder",
]


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
