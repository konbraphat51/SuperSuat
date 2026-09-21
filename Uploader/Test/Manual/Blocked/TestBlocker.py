"""Manual test for the Blocker implementations against the sample PDFs.

Runs the layout stage over every PDF in `../Ocr/Sample/` and writes, per
blocker and per PDF, the detected blocks as JSON plus one PNG per page with the
blocks drawn on it, into `Output/<blocker>/`. Nothing is sent to a paid API:
every layout model runs locally, on the GPU when there is one.

Usage (from the `Uploader` directory):

    uv run python Test/Manual/Blocked/TestBlocker.py
    uv run python Test/Manual/Blocked/TestBlocker.py --blocker yomitoku --pdf tate.pdf
    uv run python Test/Manual/Blocked/TestBlocker.py --blocker ppstructure --no-render

See TestBlocker_setup.md for the setup this needs.
"""

import argparse
import sys
import time
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

# The OCR module is imported as a top-level package (`OcrModule.…`), so the
# `Uploader` directory has to be on sys.path no matter where this is run from.
UPLOADER_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(UPLOADER_ROOT))

from OcrModule.Blocked.Blocker.Blocker import Blocker  # noqa: E402
from OcrModule.Blocked.Blocker.BlockRenderer import BlockRenderer  # noqa: E402
from OcrModule.Blocked.Schema import BlockType  # noqa: E402

SAMPLE_DIR = Path(__file__).resolve().parents[1] / "Ocr" / "Sample"
OUTPUT_DIR = Path(__file__).resolve().parent / "Output"

# 200 DPI, as in TestLinear: the layout models see the same page images the
# OCR step will be given.
DEFAULT_DPI = 200


def build_yomitoku(device: str | None) -> Blocker:
    """The yomitoku blocker, imported only when it is the one asked for."""
    from OcrModule.Blocked.Blocker.Yomitoku import YomitokuBlocker

    return YomitokuBlocker(device=device)


def build_doclayout(device: str | None) -> Blocker:
    """The DocLayout-YOLO blocker, imported only when it is the one asked for."""
    from OcrModule.Blocked.Blocker.DocLayoutYolo import DocLayoutYoloBlocker

    return DocLayoutYoloBlocker(device=device)


def build_ppstructure(device: str | None) -> Blocker:
    """The PP-StructureV3 blocker, imported only when it is the one asked for."""
    from OcrModule.Blocked.Blocker.PpStructure import PpStructureBlocker

    return PpStructureBlocker(device=device)


# Every blocker this test can run, by the name `--blocker` takes. The builders
# are lazy because each one loads a different heavy framework.
BLOCKER_BUILDERS = {
    "yomitoku": build_yomitoku,
    "doclayout": build_doclayout,
    "ppstructure": build_ppstructure,
}


def pdf_to_images(pdf_path: Path, dpi: int, max_pages: int | None) -> list[Image.Image]:
    """Every page of the PDF rendered to an RGB PIL image."""
    images: list[Image.Image] = []

    with fitz.open(pdf_path) as document:
        page_count = (
            len(document) if max_pages is None else min(len(document), max_pages)
        )

        for page_number in range(page_count):
            pixmap = document[page_number].get_pixmap(dpi=dpi)
            images.append(
                Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            )

    return images


# Shared by every blocker run: rendering has no state of its own.
RENDERER = BlockRenderer()


def run_one_pdf(pdf_path: Path, blocker: Blocker, output_dir: Path, args) -> Path:
    print(f"\n=== {pdf_path.name} ===", flush=True)

    images = pdf_to_images(pdf_path, args.dpi, args.max_pages)
    print(f"rendered {len(images)} page(s) at {args.dpi} DPI", flush=True)

    started_at = time.monotonic()
    result = blocker.block(images)
    elapsed = time.monotonic() - started_at

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{pdf_path.stem}.json"
    output_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    if not args.no_render:
        for page_number, page in enumerate(RENDERER.render(images, result)):
            page.save(output_dir / f"{pdf_path.stem}_p{page_number}.png")

    counts = {
        block_type.value: sum(
            1 for block in result.blocks if block.block_type is block_type
        )
        for block_type in BlockType
    }
    print(f"{len(result.blocks)} block(s) {counts} in {elapsed:.1f}s", flush=True)
    print(f"-> {output_path}", flush=True)
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--blocker",
        action="append",
        choices=sorted(BLOCKER_BUILDERS),
        help="Blocker to run. Repeatable. Defaults to every one of them.",
    )
    parser.add_argument(
        "--pdf",
        action="append",
        help="File name (or path) of a PDF to run. Repeatable. Defaults to every PDF in ../Ocr/Sample/.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=DEFAULT_DPI,
        help=f"Page render DPI (default: {DEFAULT_DPI})",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Only read the first N pages of each PDF.",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Device for the layout models, named as the chosen blocker names it ('cuda'/'cpu', 'gpu'/'cpu'). Default: the GPU when available.",
    )
    parser.add_argument(
        "--no-render",
        action="store_true",
        help="Skip the per-page PNGs and write only the JSON.",
    )
    return parser.parse_args()


def resolve_pdfs(selected: list[str] | None) -> list[Path]:
    if not selected:
        return sorted(SAMPLE_DIR.glob("*.pdf"))

    paths = []
    for name in selected:
        candidate = Path(name)
        if not candidate.is_file():
            candidate = SAMPLE_DIR / name
        if not candidate.is_file():
            raise FileNotFoundError(f"PDF not found: {name}")
        paths.append(candidate)

    return paths


def run_one_blocker(name: str, pdfs: list[Path], args) -> list[str]:
    """Runs one blocker over every PDF, returning the names of those that failed."""
    print(f"\n########## {name} ##########", flush=True)

    blocker = BLOCKER_BUILDERS[name](args.device)
    output_dir = OUTPUT_DIR / name

    failures: list[str] = []
    for pdf_path in pdfs:
        try:
            run_one_pdf(pdf_path, blocker, output_dir, args)
        except Exception as error:
            # One bad PDF should not cost the results of the others.
            print(f"FAILED {name}/{pdf_path.name}: {error}", file=sys.stderr)
            failures.append(f"{name}/{pdf_path.name}")

    return failures


def main() -> int:
    args = parse_args()

    pdfs = resolve_pdfs(args.pdf)
    if not pdfs:
        print(f"No PDFs found in {SAMPLE_DIR}", file=sys.stderr)
        return 1

    blockers = args.blocker or sorted(BLOCKER_BUILDERS)
    print(f"blockers: {', '.join(blockers)}")
    print(f"targets: {', '.join(p.name for p in pdfs)}")

    failures: list[str] = []
    for name in blockers:
        failures.extend(run_one_blocker(name, pdfs, args))

    if failures:
        print(f"\nFAILED: {', '.join(failures)}", file=sys.stderr)
        return 1

    print(f"\nAll {len(pdfs)} PDF(s) written to {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
