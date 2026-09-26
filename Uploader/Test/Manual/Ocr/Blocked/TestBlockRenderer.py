"""Manual test for BlockRenderer, independent of any layout model.

Renders the first page of a sample PDF with a handful of fabricated blocks
drawn on it, so the box/ID drawing can be checked without loading a blocker.
Writes one PNG into `Output/render/`.

Usage (from the `Uploader` directory):

    uv run python Test/Manual/Ocr/Blocked/TestBlockRenderer.py
    uv run python Test/Manual/Ocr/Blocked/TestBlockRenderer.py --pdf tate.pdf
"""

import argparse
import sys
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

# The OCR module is imported as a top-level package (`OcrModule.…`), so the
# `Uploader` directory has to be on sys.path no matter where this is run from.
UPLOADER_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(UPLOADER_ROOT))

from OcrModule.Blocked.Blocker.BlockRenderer import BlockRenderer  # noqa: E402
from OcrModule.Blocked.Schema import Block, BlockerResult  # noqa: E402

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "Sample"
OUTPUT_DIR = Path(__file__).resolve().parent / "Output" / "render"

DEFAULT_PDF = "Seaman.pdf"
DEFAULT_DPI = 200


def load_first_page(pdf_path: Path, dpi: int) -> Image.Image:
    """The first page of the PDF, rendered to an RGB PIL image."""
    with fitz.open(pdf_path) as document:
        pixmap = document[0].get_pixmap(dpi=dpi)
        return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)


def fabricated_blocks(page_size: tuple[int, int]) -> BlockerResult:
    """A handful of blocks laid out as a diagonal staircase.

    Fabricated rather than detected, so this test exercises only the
    renderer: box outlines and ID legibility.
    """
    width, height = page_size
    box_size = min(width, height) // 6

    blocks = [
        Block(
            block_id=block_id,
            page_index=0,
            bounding_box=(
                box_size * block_id,
                box_size * block_id,
                box_size * 2,
                box_size,
            ),
        )
        for block_id in range(4)
    ]
    return BlockerResult(blocks=blocks)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pdf",
        default=DEFAULT_PDF,
        help=f"File name (or path) of the sample PDF to draw on (default: {DEFAULT_PDF}).",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=DEFAULT_DPI,
        help=f"Page render DPI (default: {DEFAULT_DPI})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.is_file():
        pdf_path = SAMPLE_DIR / args.pdf
    if not pdf_path.is_file():
        print(f"PDF not found: {args.pdf}", file=sys.stderr)
        return 1

    page = load_first_page(pdf_path, args.dpi)
    result = fabricated_blocks(page.size)

    rendered = BlockRenderer().render([page], result)[0]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{pdf_path.stem}.png"
    rendered.save(output_path)

    print(f"{len(result.blocks)} block(s) drawn -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
