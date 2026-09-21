"""Manual test for LinearOcr against the sample PDFs.

Runs the Linear OCR pipeline over every PDF in `Sample/` and writes one JSON
file per PDF into `Output/`. The OCR agent and the clipper can each run on
either Amazon Bedrock or the OpenAI API, set independently via OCR_PROVIDER /
CLIPPER_PROVIDER in `.env` (or --ocr-provider / --clipper-provider) - default
is OCR on OpenAI, clipper on Bedrock, since Bedrock's Qwen models don't
support the forced tool_choice the OCR agent's structured final response
depends on (see OcrOutputSchema).

Usage (from the `Uploader` directory):

    uv run python Test/Manual/Ocr/TestLinear.py
    uv run python Test/Manual/Ocr/TestLinear.py --pdf tate.pdf --max-pages 2
    uv run python Test/Manual/Ocr/TestLinear.py --log-level DEBUG

A tqdm progress bar on stdout shows which page is being processed. Everything
else (every model message, tool call/result, and clipper invocation, at
--log-level INFO or above) is written to the log file instead (see
--log-file), to help diagnose where a slow run is spending its time.

See TestLinear_setup.md for the AWS setup this needs.
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

import fitz  # PyMuPDF
from PIL import Image

# The OCR module is imported as a top-level package (`OcrModule.…`), so the
# `Uploader` directory has to be on sys.path no matter where this is run from.
UPLOADER_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(UPLOADER_ROOT))

from dotenv import load_dotenv  # noqa: E402

from OcrModule.Linear.LinearOcr import LinearOcr  # noqa: E402
from OcrModule.LlmHelper import (  # noqa: E402
    build_image_message_bedrock,
    build_image_message_openai,
)

SAMPLE_DIR = Path(__file__).resolve().parent / "Sample"
OUTPUT_DIR = Path(__file__).resolve().parent / "Output"

PROVIDERS = ("bedrock", "openai")

# Which provider each role uses by default when OCR_PROVIDER / CLIPPER_PROVIDER
# isn't set - Bedrock's Qwen models don't support the forced tool_choice the
# OCR agent's structured final response depends on (see OcrOutputSchema), so
# the OCR agent defaults to OpenAI; the clipper has no such requirement and
# defaults to Bedrock.
DEFAULT_OCR_PROVIDER = "openai"
DEFAULT_CLIPPER_PROVIDER = "bedrock"

# Default model id per provider, used for whichever role (OCR or clipper)
# lands on that provider. Override with OCR_MODEL_ID / CLIPPER_MODEL_ID for a
# fully qualified id (e.g. a Bedrock inference profile prefixed with the
# region), or if the OpenAI model id below isn't the exact one to call.
DEFAULT_MODEL_IDS = {
    "bedrock": "qwen.qwen3-vl-235b-a22b",
    "openai": "gpt-5.6-luna",
}
DEFAULT_REGION = "us-west-2"

# 200 DPI keeps small kana and subscripts legible without blowing up the
# base64 payload that every page image is sent as.
DEFAULT_DPI = 200
DEFAULT_MAX_TOKENS = 8192


def build_bedrock_model(model_id: str, region: str, api_key: str | None):
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


def build_openai_model(model_id: str, api_key: str | None):
    """An OpenAI chat model. Imported lazily so that `--help` works without
    langchain-openai installed."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model_id,
        max_tokens=DEFAULT_MAX_TOKENS,
        temperature=0,
        **({"api_key": api_key} if api_key else {}),
    )


def build_model(
    provider: str,
    model_id: str,
    region: str,
    aws_api_key: str | None,
    openai_api_key: str | None,
):
    if provider == "openai":
        return build_openai_model(model_id, openai_api_key)
    return build_bedrock_model(model_id, region, aws_api_key)


def image_message_builder_for(provider: str):
    return (
        build_image_message_openai
        if provider == "openai"
        else build_image_message_bedrock
    )


def pdf_to_images(
    pdf_path: Path, dpi: int, max_pages: int | None
) -> list[Image.Image]:
    """Every page of the PDF rendered to an RGB PIL image."""
    images: list[Image.Image] = []

    with fitz.open(pdf_path) as document:
        page_count = (
            len(document)
            if max_pages is None
            else min(len(document), max_pages)
        )

        for page_number in range(page_count):
            pixmap = document[page_number].get_pixmap(dpi=dpi)
            images.append(
                Image.frombytes(
                    "RGB", (pixmap.width, pixmap.height), pixmap.samples
                )
            )

    return images


def run_one_pdf(
    pdf_path: Path,
    args,
    aws_api_key: str | None,
    openai_api_key: str | None,
) -> Path:
    print(f"\n=== {pdf_path.name} ===", flush=True)

    images = pdf_to_images(pdf_path, args.dpi, args.max_pages)
    print(f"rendered {len(images)} page(s) at {args.dpi} DPI", flush=True)

    ocr = LinearOcr(
        ocr_model=build_model(
            args.ocr_provider,
            args.ocr_model,
            args.region,
            aws_api_key,
            openai_api_key,
        ),
        clipper_model=build_model(
            args.clipper_provider,
            args.clipper_model,
            args.region,
            aws_api_key,
            openai_api_key,
        ),
        image_message_builder=image_message_builder_for(args.ocr_provider),
        clipper_image_message_builder=image_message_builder_for(
            args.clipper_provider
        ),
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
        help="Only read the first N pages of each PDF. Useful for a cheap smoke run.",
    )
    parser.add_argument(
        "--ocr-provider",
        choices=PROVIDERS,
        default=None,
        help=f"Provider for the OCR agent. Default: OCR_PROVIDER in .env, else {DEFAULT_OCR_PROVIDER!r}.",
    )
    parser.add_argument(
        "--clipper-provider",
        choices=PROVIDERS,
        default=None,
        help=f"Provider for the clipper. Default: CLIPPER_PROVIDER in .env, else {DEFAULT_CLIPPER_PROVIDER!r}.",
    )
    parser.add_argument(
        "--ocr-model",
        default=None,
        help="Model id for the OCR agent. Default: OCR_MODEL_ID in .env, else a per-provider default.",
    )
    parser.add_argument(
        "--clipper-model",
        default=None,
        help="Model id for the clipper. Default: CLIPPER_MODEL_ID in .env, else a per-provider default.",
    )
    parser.add_argument(
        "--region",
        default=os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or DEFAULT_REGION,
        help="Bedrock region, used by whichever role (OCR/clipper) is on Bedrock.",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Verbosity of OcrModule.Linear's logging (model output, tool calls/results). Default: INFO.",
    )
    parser.add_argument(
        "--log-file",
        default=str(OUTPUT_DIR / "TestLinear.log"),
        help="Where to write the log described above. Default: Output/TestLinear.log (overwritten every run).",
    )
    args = parser.parse_args()

    # Resolved here (--ocr-model/--clipper-model default to None above) rather
    # than as argparse defaults, since the sensible default model id depends
    # on which provider ends up selected - which itself may come from .env
    # rather than the CLI.
    args.ocr_provider = args.ocr_provider or os.getenv(
        "OCR_PROVIDER", DEFAULT_OCR_PROVIDER
    )
    args.clipper_provider = args.clipper_provider or os.getenv(
        "CLIPPER_PROVIDER", DEFAULT_CLIPPER_PROVIDER
    )
    args.ocr_model = (
        args.ocr_model
        or os.getenv("OCR_MODEL_ID")
        or DEFAULT_MODEL_IDS[args.ocr_provider]
    )
    args.clipper_model = (
        args.clipper_model
        or os.getenv("CLIPPER_MODEL_ID")
        or DEFAULT_MODEL_IDS[args.clipper_provider]
    )

    return args


def configure_logging(log_level: str, log_file: Path) -> None:
    """Writes OcrModule.Linear's logging (the model's reasoning, every tool
    call/result, and the clipper's output) to `log_file`, keeping stdout free
    for the tqdm progress bar."""
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        filename=log_file,
        filemode="w",
        encoding="utf-8",
    )
    # boto3/botocore log every HTTP request at INFO/DEBUG, which would drown
    # out the OCR-specific logging above; keep them quiet regardless of
    # --log-level.
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


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
    # Must run before parse_args(): it reads os.environ (OCR_PROVIDER,
    # CLIPPER_PROVIDER, OCR_MODEL_ID, CLIPPER_MODEL_ID, AWS_REGION, ...), so
    # .env has to be loaded first or those defaults silently fall back to the
    # hardcoded ones.
    load_dotenv(UPLOADER_ROOT / ".env")
    args = parse_args()
    log_file = Path(args.log_file)
    configure_logging(args.log_level, log_file)

    # The .env of this project stores the Bedrock short-term API key under its
    # own name; langchain-aws reads AWS_BEARER_TOKEN_BEDROCK. Passing it
    # explicitly also leaves the door open for plain IAM credentials, in which
    # case there is no key here and boto3's own resolution takes over.
    aws_api_key = os.getenv("AWS_BEDROCK_SHORT_API_KEY") or os.getenv(
        "AWS_BEARER_TOKEN_BEDROCK"
    )

    if aws_api_key:
        # Bearer-token auth never consults the AWS profile, but botocore still
        # resolves the default profile while building the client and fails hard
        # on providers it lacks the extras for (`login_session` needs
        # botocore[crt]). Pointing the config file at nothing keeps an unrelated
        # local AWS setup from breaking a run that does not depend on it.
        os.environ["AWS_CONFIG_FILE"] = os.devnull
        os.environ.pop("AWS_PROFILE", None)

    # ChatOpenAI would otherwise fail deep inside the OCR agent's first call;
    # failing here instead makes a missing key obvious immediately. Only
    # required when a role actually landed on openai.
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if (
        "openai" in (args.ocr_provider, args.clipper_provider)
        and not openai_api_key
    ):
        print(
            "ERROR: OPENAI_API_KEY is not set, but OCR_PROVIDER/CLIPPER_PROVIDER "
            "selects openai for at least one role.",
            file=sys.stderr,
        )
        return 1

    pdfs = resolve_pdfs(args.pdf)
    if not pdfs:
        print(f"No PDFs found in {SAMPLE_DIR}", file=sys.stderr)
        return 1

    print(f"OCR model: {args.ocr_model} [{args.ocr_provider}]")
    print(f"clipper model: {args.clipper_model} [{args.clipper_provider}]")
    if "bedrock" in (args.ocr_provider, args.clipper_provider):
        print(f"region: {args.region}")
    print(f"targets: {', '.join(p.name for p in pdfs)}")
    print(f"log: {log_file}")

    failures: list[str] = []
    for pdf_path in pdfs:
        try:
            run_one_pdf(pdf_path, args, aws_api_key, openai_api_key)
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
