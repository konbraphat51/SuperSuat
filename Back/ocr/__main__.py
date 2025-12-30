"""Command-line interface for the OCR module."""

import argparse
import logging

from . import process_pdf_to_folder


def main() -> None:
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        prog="ocr",
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
