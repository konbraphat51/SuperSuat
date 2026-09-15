"""Manual test for LinearOcr against the sample PDFs.

Runs the Linear OCR pipeline over every PDF in `Sample/` using Amazon Bedrock
as the provider, and writes one JSON file per PDF into `Output/`.

Usage (from the `Uploader` directory):

    uv run python Test/Manual/Ocr/TestLinear.py
    uv run python Test/Manual/Ocr/TestLinear.py --pdf tate.pdf --max-pages 2

See TestLinear-test.md for the AWS setup this needs.
"""

import argparse
import json
import os
import sys
import time
import traceback
from dataclasses import asdict
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

# The OCR module is imported as a top-level package (`OcrModule.…`), so the
# `Uploader` directory has to be on sys.path no matter where this is run from.
UPLOADER_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(UPLOADER_ROOT))

from dotenv import load_dotenv  # noqa: E402

from OcrModule.Linear.LinearOcr import LinearOcr  # noqa: E402
from OcrModule.LlmHelper import build_image_message_bedrock  # noqa: E402

SAMPLE_DIR = Path(__file__).resolve().parent / "Sample"
OUTPUT_DIR = Path(__file__).resolve().parent / "Output"

# Both the OCR agent and the clipper run on the same Bedrock model. Override
# with OCR_MODEL_ID / CLIPPER_MODEL_ID if the account needs a fully qualified
# model id (e.g. an inference profile prefixed with the region).
DEFAULT_MODEL_ID = "qwen.qwen3-vl-235b-a22b"
DEFAULT_REGION = "us-west-2"

# 200 DPI keeps small kana and subscripts legible without blowing up the
# base64 payload that every page image is sent as.
DEFAULT_DPI = 200
DEFAULT_MAX_TOKENS = 8192


def build_model(model_id: str, region: str, api_key: str | None):
    """A Bedrock chat model. Imported lazily so that `--help` works without
    langchain-aws installed."""
    from langchain_aws import ChatBedrockConverse

    return ChatBedrockConverse(
        model=model_id,
        region_name=region,
        max_tokens=DEFAULT_MAX_TOKENS,
        temperature=0,
        **({"bedrock_api_key": api_key} if api_key else {}),
    )


def pdf_to_images(pdf_path: Path, dpi: int, max_pages: int | None) -> list[Image.Image]:
    """Every page of the PDF rendered to an RGB PIL image."""
    images: list[Image.Image] = []

    with fitz.open(pdf_path) as document:
        page_count = len(document) if max_pages is None else min(len(document), max_pages)

        for page_number in range(page_count):
            pixmap = document[page_number].get_pixmap(dpi=dpi)
            images.append(
                Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            )

    return images


def run_one_pdf(pdf_path: Path, args, api_key: str | None) -> Path:
    print(f"\n=== {pdf_path.name} ===", flush=True)

    images = pdf_to_images(pdf_path, args.dpi, args.max_pages)
    print(f"rendered {len(images)} page(s) at {args.dpi} DPI", flush=True)

    ocr = LinearOcr(
        ocr_model=build_model(args.ocr_model, args.region, api_key),
        clipper_model=build_model(args.clipper_model, args.region, api_key),
        image_message_builder=build_image_message_bedrock,
    )

    started_at = time.monotonic()
    result = ocr.ocr(images)
    elapsed = time.monotonic() - started_at

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{pdf_path.stem}.json"
    output_path.write_text(
        json.dumps(asdict(result), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"done in {elapsed:.1f}s -> {output_path}", flush=True)
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pdf",
        action="append",
        help="File name (or path) of a PDF to run. Repeatable. Defaults to every PDF in Sample/.",
    )
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI, help=f"Page render DPI (default: {DEFAULT_DPI})")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Only read the first N pages of each PDF. Useful for a cheap smoke run.",
    )
    parser.add_argument("--ocr-model", default=os.getenv("OCR_MODEL_ID", DEFAULT_MODEL_ID))
    parser.add_argument("--clipper-model", default=os.getenv("CLIPPER_MODEL_ID", DEFAULT_MODEL_ID))
    parser.add_argument("--region", default=os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or DEFAULT_REGION)
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


def main() -> int:
    args = parse_args()
    load_dotenv(UPLOADER_ROOT / ".env")

    # The .env of this project stores the Bedrock short-term API key under its
    # own name; langchain-aws reads AWS_BEARER_TOKEN_BEDROCK. Passing it
    # explicitly also leaves the door open for plain IAM credentials, in which
    # case there is no key here and boto3's own resolution takes over.
    api_key = os.getenv("AWS_BEDROCK_SHORT_API_KEY") or os.getenv("AWS_BEARER_TOKEN_BEDROCK")

    if api_key:
        # Bearer-token auth never consults the AWS profile, but botocore still
        # resolves the default profile while building the client and fails hard
        # on providers it lacks the extras for (`login_session` needs
        # botocore[crt]). Pointing the config file at nothing keeps an unrelated
        # local AWS setup from breaking a run that does not depend on it.
        os.environ["AWS_CONFIG_FILE"] = os.devnull
        os.environ.pop("AWS_PROFILE", None)

    pdfs = resolve_pdfs(args.pdf)
    if not pdfs:
        print(f"No PDFs found in {SAMPLE_DIR}", file=sys.stderr)
        return 1

    print(f"model: {args.ocr_model} (clipper: {args.clipper_model}) @ {args.region}")
    print(f"targets: {', '.join(p.name for p in pdfs)}")

    failures: list[str] = []
    for pdf_path in pdfs:
        try:
            run_one_pdf(pdf_path, args, api_key)
        except Exception:
            # One bad PDF should not cost the results of the others.
            traceback.print_exc()
            failures.append(pdf_path.name)

    if failures:
        print(f"\nFAILED: {', '.join(failures)}", file=sys.stderr)
        return 1

    print(f"\nAll {len(pdfs)} PDF(s) written to {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
