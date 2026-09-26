"""Manual test for MdWriterOcr against the sample PDFs.

Runs the MdWriter pipeline over the PDFs in `Test/Manual/Ocr/Sample/` and
writes, per PDF, into `Output/<detector>/<run name>/` (the model id by default):

- `<stem>.md`: the stitched Markdown, as the model wrote it
- `<stem>.json`: the document tree parsed from it
- `<stem>.usage.txt`: every page's tokens and, for a model in
  UsageCost.PRICING, what they cost
- `<stem>/page_<N>.png`: every page as the model saw it, figures boxed

The model runs on the OpenAI API or on Amazon Bedrock, chosen by
OCR_PROVIDER / OCR_MODEL_ID in `.env` (or --provider / --model).

Usage (from the `Uploader` directory):

    uv run python Test/Manual/MdWriter/TestMdWriter.py --pdf shido_math.pdf --detector doclayout
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

from OcrModule.LlmHelper import MODEL_IMAGE_MAX_EDGE  # noqa: E402
from OcrModule.MdWriter.FigureDetector import FigureDetector  # noqa: E402
from OcrModule.MdWriter.MdWriterOcr import MdWriterOcr  # noqa: E402
from OcrModule.MdWriter.Assembly.PageJoin import JoinJudge  # noqa: E402
from OcrModule.MdWriter.Parser.MarkdownParser import parse_markdown  # noqa: E402
from OcrModule.MdWriter.ReferenceReader import ReferenceReader  # noqa: E402
from OcrModule.MdWriter.Transcriber.PageTranscriber import (  # noqa: E402
    DEFAULT_MIN_AGREEMENT,
    Escalation,
    PageTranscriber,
)
from UsageCost import UsageRecorder, format_report  # noqa: E402

SAMPLE_DIR = UPLOADER_ROOT / "Test" / "Manual" / "Ocr" / "Sample"
OUTPUT_DIR = Path(__file__).resolve().parent / "Output"

PROVIDERS = ("openai", "bedrock")
DETECTORS = ("doclayout", "yomitoku", "ppstructure")
REFERENCES = ("none", "yomitoku")

DEFAULT_PROVIDER = "openai"
DEFAULT_MODEL_IDS = {
    "bedrock": "qwen.qwen3-vl-235b-a22b",
    "openai": "gpt-5.6-luna",
}
DEFAULT_REGION = "us-west-2"
DEFAULT_DPI = 200

# One answer carries one page, with room left for the model's reasoning.
DEFAULT_MAX_TOKENS = 16000

# One request per page, so more of them go out at once than pages did before.
DEFAULT_MAX_PARALLEL = 8


def build_model(
    args: argparse.Namespace,
    recorder: UsageRecorder,
    model_id: str,
    reasoning_effort: str | None,
) -> Any:
    """A chat model of the chosen provider, reporting its usage to `recorder`.
    Imported lazily so that `--help` works without the provider's package."""
    if args.provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model_id,
            use_responses_api=True,
            max_tokens=args.max_tokens,
            callbacks=[recorder],
            **({"reasoning_effort": reasoning_effort} if reasoning_effort else {}),
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
        model=model_id,
        region_name=args.region,
        max_tokens=args.max_tokens,
        temperature=0,
        callbacks=[recorder],
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


def build_reference_reader(name: str) -> ReferenceReader | None:
    """The reference reader named on the command line, or None for none."""
    if name == "none":
        return None

    from OcrModule.MdWriter import ReferenceReader as readers

    return readers.YomitokuReferenceReader()


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


def output_dir_of(args: argparse.Namespace) -> Path:
    """Where the results of this detector and run go."""
    return OUTPUT_DIR / args.detector / (args.run_name or args.model)


def run_one_pdf(
    pdf_path: Path,
    ocr: MdWriterOcr,
    recorder: UsageRecorder,
    args: argparse.Namespace,
) -> None:
    """Reads one PDF and writes its Markdown, tree, usage and rendered pages out."""
    print(f"\n=== {pdf_path.name} ===", flush=True)
    recorder.reset()

    images = pdf_to_images(pdf_path, args.dpi, args.max_pages)
    print(f"rendered {len(images)} page(s) at {args.dpi} DPI", flush=True)

    started_at = time.monotonic()
    draft = ocr.write_markdown(images)
    result = parse_markdown(draft.markdown, draft.figures)
    elapsed = time.monotonic() - started_at

    output_dir = output_dir_of(args)
    pages_dir = output_dir / pdf_path.stem
    pages_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / f"{pdf_path.stem}.md").write_text(draft.markdown, encoding="utf-8")
    (output_dir / f"{pdf_path.stem}.json").write_text(
        json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for page_index, page in enumerate(draft.rendered_pages):
        page.save(pages_dir / f"page_{page_index}.png")

    report = format_report(recorder.pages)
    (output_dir / f"{pdf_path.stem}.usage.txt").write_text(
        f"{pdf_path.name}: {len(images)} page(s) in {elapsed:.1f}s\n{report}\n",
        encoding="utf-8",
    )

    print(
        f"done in {elapsed:.1f}s: {len(draft.figures)} figure(s) -> {output_dir}",
        flush=True,
    )
    print(report, flush=True)


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
    parser.add_argument(
        "--max-parallel",
        type=int,
        default=DEFAULT_MAX_PARALLEL,
        help="Most pages sent to the model at once.",
    )
    parser.add_argument("--max-pages", type=int, default=None)
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI)
    parser.add_argument(
        "--image-max-edge",
        type=int,
        default=MODEL_IMAGE_MAX_EDGE,
        help="Longest side a page is sent to the model at, in pixels.",
    )
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
        "--join-model",
        default=None,
        help="Model settling the page turns two pages disagree on. Defaults to --model.",
    )
    parser.add_argument("--join-reasoning-effort", default=None)
    parser.add_argument(
        "--reference",
        choices=REFERENCES,
        default="none",
        help="Local OCR whose text the model checks its characters against.",
    )
    parser.add_argument(
        "--escalate-model",
        default=None,
        help="Model a page is written again with when it agrees too little with its reference.",
    )
    parser.add_argument("--min-agreement", type=float, default=DEFAULT_MIN_AGREEMENT)
    parser.add_argument(
        "--run-name",
        default=None,
        help="Output folder under Output/<detector>/, to keep variants apart. Defaults to the model id.",
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
    args.join_model = args.join_model or args.model
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
    print(f"detector: {args.detector}")
    print(f"targets: {', '.join(p.name for p in pdfs)}")
    print(f"log: {args.log_file}")

    recorder = UsageRecorder()
    ocr = MdWriterOcr(
        figure_detector=build_detector(args.detector),
        transcriber=PageTranscriber(
            build_model(args, recorder, args.model, args.reasoning_effort),
            image_max_edge=args.image_max_edge,
            escalation=(
                Escalation(
                    build_model(args, recorder, args.escalate_model, None),
                    args.min_agreement,
                )
                if args.escalate_model
                else None
            ),
        ),
        reference_reader=build_reference_reader(args.reference),
        join_judge=JoinJudge(
            build_model(args, recorder, args.join_model, args.join_reasoning_effort)
        ),
        max_parallel_pages=args.max_parallel,
    )

    failures: list[str] = []
    for pdf_path in pdfs:
        try:
            run_one_pdf(pdf_path, ocr, recorder, args)
        except Exception:
            # one bad PDF should not cost the results of the others
            traceback.print_exc()
            failures.append(pdf_path.name)

    if failures:
        print(f"\nFAILED: {', '.join(failures)}", file=sys.stderr)
        return 1

    print(f"\nAll {len(pdfs)} PDF(s) written to {output_dir_of(args)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
