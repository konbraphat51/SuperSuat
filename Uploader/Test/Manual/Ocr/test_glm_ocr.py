"""
Manual test: GLM-OCR on shido_math.pdf
Run from the Uploader/ directory:
    uv run python Test/Manual/Ocr/test_glm_ocr.py
"""

import sys
from pathlib import Path

import fitz  # pymupdf

sys.path.insert(0, str(Path(__file__).parents[3]))

from OcrModule.GlmOcr.Ocr import GlmOcrOcr

PDF_PATH = Path(__file__).parent / "Sample" / "shido_math.pdf"
DPI = 96


def pdf_to_images(path: Path, dpi: int = DPI) -> list[bytes]:
    doc = fitz.open(path)
    images = []
    for page in doc:
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        images.append(pix.tobytes("png"))
    doc.close()
    return images


def print_result(result) -> None:
    for i, block in enumerate(result.blocks):
        btype = block.block_type
        print(f"\n--- block {i:03d}  [{btype}] ---")

        if btype == "section":
            print(f"  level : {block.level}")
            print(f"  text  : {block.text}")
        elif btype == "text":
            print(f"  text  : {block.text[:300]}")
        elif btype == "table":
            print(f"  caption : {block.caption}")
            print(f"  markdown:\n{block.text[:500]}")
        elif btype == "equation":
            print(f"  caption : {block.caption}")
            print(f"  latex   : {block.text[:300]}")
        elif btype == "image":
            print(f"  caption    : {block.caption}")
            print(f"  image_size : {len(block.image_data)} bytes")
        elif btype == "footer":
            print(f"  text : {block.text}")


def main() -> None:
    print(f"PDF: {PDF_PATH}")
    print(f"Loading {PDF_PATH.name} ...")
    images = pdf_to_images(PDF_PATH)
    print(f"Pages: {len(images)}")

    print("\nInitializing GLM-OCR (model download on first run) ...")
    try:
        ocr = GlmOcrOcr()
    except Exception as e:
        print(f"ERROR during init: {type(e).__name__}: {e}")
        raise

    print("\nRunning OCR ...")
    try:
        result = ocr.ocr(images)
    except Exception as e:
        print(f"ERROR during OCR: {type(e).__name__}: {e}")
        raise

    print(f"\n{'='*60}")
    print(f"Total blocks: {len(result.blocks)}")
    print(f"{'='*60}")
    print_result(result)


if __name__ == "__main__":
    main()
