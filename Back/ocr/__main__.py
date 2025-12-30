"""Command-line interface for the OCR module."""

import argparse
import logging
from pathlib import Path

from .config import ProcessorConfig, AcceleratorDevice
from .exporters import OutputWriter
from .processor import DoclingProcessor


def main() -> None:
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        prog="ocr",
        description="Process PDF files using Docling to extract OCR data, "
                    "structure data, and export images for equations, figures, and tables."
    )
    parser.add_argument("pdf_path", type=str, help="Path to the PDF file to process")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "-a", "--accelerator",
        type=str,
        choices=["auto", "cpu", "cuda", "mps"],
        default="auto",
        help="Accelerator device: auto, cpu, cuda (NVIDIA), mps (Apple Silicon)"
    )
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    # Create config with specified accelerator
    config = ProcessorConfig(accelerator=AcceleratorDevice(args.accelerator))
    processor = DoclingProcessor(config)
    
    pdf_path = Path(args.pdf_path)
    output_folder = pdf_path.parent / pdf_path.stem
    
    output = processor.process(pdf_path, output_folder)
    OutputWriter.write_json(output, output_folder / "output.json")
    
    print(f"Output saved to: {output_folder}")


if __name__ == "__main__":
    main()
