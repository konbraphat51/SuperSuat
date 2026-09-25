"""Manual test for MdWriterOcr against the sample PDFs.

Runs the MdWriter pipeline over the PDFs in `Test/Manual/Ocr/Sample/` and
writes, per PDF, into `Output/<detector>/`:

- `<stem>.md`: the stitched Markdown, as the model wrote it
- `<stem>.json`: the document tree parsed from it
- `<stem>/page_<N>.png`: every page as the model saw it, figures boxed

The model runs on the OpenAI API or on Amazon Bedrock, chosen by
OCR_PROVIDER / OCR_MODEL_ID in `.env` (or --provider / --model).

Usage (from the `Uploader` directory):

    uv run python Test/Manual/MdWriter/TestMdWriter.py --pdf shido_math.pdf --detector doclayout --batch-size 2
    uv run python Test/Manual/MdWriter/TestMdWriter.py --max-pages 5

See TestMdWriter_setup.md for what this needs.
"""

import argparse
import json
import logging
import os
import sys
import time
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from PIL import Image

# The OCR module is imported as a top-level package (`OcrModule.…`), so the
# `Uploader` directory has to be on sys.path no matter where this is run from.
UPLOADER_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(UPLOADER_ROOT))

from dotenv import load_dotenv  # noqa: E402

from OcrModule.MdWriter.FigureDetector import FigureDetector  # noqa: E402
from OcrModule.MdWriter.MdWriterOcr import DEFAULT_BATCH_SIZE, MdWriterOcr  # noqa: E402
from OcrModule.MdWriter.MarkdownParser import parse_markdown  # noqa: E402
from OcrModule.MdWriter.Transcriber.BatchTranscriber import (  # noqa: E402
    BatchTranscriber,
)

SAMPLE_DIR = UPLOADER_ROOT / "Test" / "Manual" / "Ocr" / "Sample"
OUTPUT_DIR = Path(__file__).resolve().parent / "Output"

PROVIDERS = ("openai", "bedrock")
DETECTORS = ("doclayout", "yomitoku", "ppstructure")

DEFAULT_PROVIDER = "openai"
DEFAULT_MODEL_IDS = {
    "bedrock": "qwen.qwen3-vl-235b-a22b",
    "openai": "gpt-5.6-luna",
}
DEFAULT_REGION = "us-west-2"
DEFAULT_DPI = 200

# One answer carries a whole batch of pages, far more than one page's worth.
DEFAULT_MAX_TOKENS = 32000


def build_model(args: argparse.Namespace) -> Any:
    """The chat model the batches are written with. Imported lazily so that
    `--help` works without the provider's package."""
    if args.provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=args.model,
            use_responses_api=True,
            max_tokens=args.max_tokens,
            **(
                {"reasoning_effort": args.reasoning_effort}
                if args.reasoning_effort
                else {}
            ),
        )

    from langchain_aws import ChatBedrockConverse

    api_key = os.getenv("AWS_BEDROCK_SHORT_API_KEY") or os.getenv(
        "AWS_BEARER_TOKEN_BEDROCK"
    )
    if api_key:
        # bearer-token auth never reads the AWS profile, which may be broken locally
        os.environ["AWS_CONFIG_FILE"] = os.devnull
        os.environ.pop("AWS_PROFILE", None)

    return ChatBedrockConverse(
        model=args.model,
        region_name=args.region,
        max_tokens=args.max_tokens,
        temperature=0,
        **({"bedrock_api_key": api_key} if api_key else {}),
    )


def build_detector(name: str) -> FigureDetector:
    """The figure detector named on the command line, its framework loaded now."""
    from OcrModule.MdWriter import FigureDetector as detectors

    if name == "yomitoku":
        return detectors.YomitokuFigureDetector()
    if name == "ppstructure":
        return detectors.PpStructureFigureDetector()
    return detectors.DocLayoutYoloFigureDetector()


def pdf_to_images(pdf_path: Path, dpi: int, max_pages: int | None) -> list[Any]:
    """Every page of the PDF rendered to an RGB PIL image."""
    images = []

    with fitz.open(pdf_path) as document:
        page_count = (
            len(document) if max_pages is None else min(len(document), max_pages)
        )
        for page_index in range(page_count):
            pixmap = document[page_index].get_pixmap(dpi=dpi)
            images.append(
                Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            )

    return images


def run_one_pdf(pdf_path: Path, ocr: MdWriterOcr, args: argparse.Namespace) -> None:
    """Reads one PDF and writes its Markdown, tree and rendered pages out."""
    print(f"\n=== {pdf_path.name} ===", flush=True)

    images = pdf_to_images(pdf_path, args.dpi, args.max_pages)
    print(f"rendered {len(images)} page(s) at {args.dpi} DPI", flush=True)

    started_at = time.monotonic()
    draft = ocr.write_markdown(images)
    result = parse_markdown(draft.markdown, draft.figures)
    elapsed = time.monotonic() - started_at

    output_dir = OUTPUT_DIR / args.detector
    pages_dir = output_dir / pdf_path.stem
    pages_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / f"{pdf_path.stem}.md").write_text(draft.markdown, encoding="utf-8")
    (output_dir / f"{pdf_path.stem}.json").write_text(
        json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for page_index, page in enumerate(draft.rendered_pages):
        page.save(pages_dir / f"page_{page_index}.png")

    print(
        f"done in {elapsed:.1f}s: {len(draft.figures)} figure(s) -> {output_dir}",
        flush=True,
    )


def resolve_pdfs(selected: list[str] | None) -> list[Path]:
    """The PDFs asked for, by path or by name in the sample folder."""
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--pdf",
        action="append",
        help="File name (or path) of a PDF to run. Repeatable. Defaults to every sample PDF.",
    )
    parser.add_argument("--detector", choices=DETECTORS, default="doclayout")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument(
        "--max-parallel",
        type=int,
        default=4,
        help="Most batches sent to the model at once.",
    )
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI)
    parser.add_argument("--provider", choices=PROVIDERS, default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument(
        "--region",
        default=os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or DEFAULT_REGION,
    )
    parser.add_argument(
        "--reasoning-effort", default=os.getenv("OPENAI_REASONING_EFFORT")
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    parser.add_argument("--log-file", default=str(OUTPUT_DIR / "TestMdWriter.log"))
    args = parser.parse_args()

    args.provider = args.provider or os.getenv("OCR_PROVIDER", DEFAULT_PROVIDER)
    args.model = (
        args.model or os.getenv("OCR_MODEL_ID") or DEFAULT_MODEL_IDS[args.provider]
    )
    return args


def configure_logging(log_level: str, log_file: Path) -> None:
    """Writes the pipeline's logging to `log_file`, keeping stdout for the progress bars."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        filename=log_file,
        filemode="w",
        encoding="utf-8",
    )
    for noisy in ("boto3", "botocore", "urllib3", "httpx", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def main() -> int:
    # .env is read before the arguments, whose defaults come from it
    load_dotenv(UPLOADER_ROOT / ".env")
    args = parse_args()
    configure_logging(args.log_level, Path(args.log_file))

    if args.provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not set.", file=sys.stderr)
        return 1

    pdfs = resolve_pdfs(args.pdf)
    print(f"model: {args.model} [{args.provider}]")
    print(f"detector: {args.detector}, batch size: {args.batch_size}")
    print(f"targets: {', '.join(p.name for p in pdfs)}")
    print(f"log: {args.log_file}")

    ocr = MdWriterOcr(
        figure_detector=build_detector(args.detector),
        transcriber=BatchTranscriber(build_model(args)),
        batch_size=args.batch_size,
        max_parallel_batches=args.max_parallel,
    )

    failures: list[str] = []
    for pdf_path in pdfs:
        try:
            run_one_pdf(pdf_path, ocr, args)
        except Exception:
            # one bad PDF should not cost the results of the others
            traceback.print_exc()
            failures.append(pdf_path.name)

    if failures:
        print(f"\nFAILED: {', '.join(failures)}", file=sys.stderr)
        return 1

    print(f"\nAll {len(pdfs)} PDF(s) written to {OUTPUT_DIR / args.detector}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
