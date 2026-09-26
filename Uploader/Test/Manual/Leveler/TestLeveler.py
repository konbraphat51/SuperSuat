"""Manual test for OcrResultLeveler against saved OCR results of the sample PDFs.

Reads every `Input/<stem>.json` (an OcrResult written by TestMdWriter), renders
`Test/Manual/Ocr/Sample/<stem>.pdf` at the DPI it was read at, levels its
headings, and writes into `Output/<run name>/` (the model id by default):

- `<stem>.json`: the nested OcrResult
- `<stem>.outline.txt`: every heading, indented by its level, with its page
- `<stem>.usage.txt`: the tokens the run used and, for a model in
  UsageCost.PRICING, what they cost

Where `GroundTruth/<stem>.json` exists, the levels are scored against it.

Usage (from the `Uploader` directory):

    uv run python Test/Manual/Leveler/TestLeveler.py
    uv run python Test/Manual/Leveler/TestLeveler.py --input shido_math --model gpt-6-luna

See TestLeveler_setup.md for what this needs.
"""

import argparse
import json
import logging
import os
import sys
import threading
import time
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Any
from uuid import UUID

import fitz  # PyMuPDF
from PIL import Image

# The Leveler and the OCR module are imported as top-level packages, so the
# `Uploader` directory has to be on sys.path no matter where this is run from.
UPLOADER_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(UPLOADER_ROOT))
sys.path.insert(0, str(UPLOADER_ROOT / "Test" / "Manual" / "MdWriter"))

from dotenv import load_dotenv  # noqa: E402
from langchain_core.callbacks import BaseCallbackHandler  # noqa: E402
from langchain_core.messages import AIMessage, BaseMessage  # noqa: E402
from langchain_core.outputs import ChatGeneration, LLMResult  # noqa: E402

from Leveler.OcrResultLeveler import OcrResultLeveler  # noqa: E402
from OcrModule.OcrSchema import (  # noqa: E402
    OcrResult,
    OcrResultBlock,
    OcrResultBlockFigure,
    OcrResultBlockTableOfContents,
    OcrResultBlockText,
    OcrResultSection,
    TableOfContentsEntry,
)
from UsageCost import PageUsage, format_report  # noqa: E402

HERE = Path(__file__).resolve().parent
INPUT_DIR = HERE / "Input"
GROUND_TRUTH_DIR = HERE / "GroundTruth"
OUTPUT_DIR = HERE / "Output"
SAMPLE_DIR = UPLOADER_ROOT / "Test" / "Manual" / "Ocr" / "Sample"

DEFAULT_MODEL_ID = "gpt-6-sol"

# The DPI TestMdWriter renders at, which the page indexes of Input/ refer to.
DEFAULT_DPI = 200

DEFAULT_MAX_TOKENS = 16000


class UsageTotal(BaseCallbackHandler):
    """Adds up the usage of every chat model request, all as one row."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._models: dict[UUID, str] = {}
        self.usage = PageUsage()

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Notes which model a request goes to."""
        params = kwargs.get("invocation_params") or {}
        with self._lock:
            self._models[run_id] = str(params.get("model") or "?")

    def on_llm_end(self, response: LLMResult, *, run_id: UUID, **kwargs: Any) -> None:
        """Counts a finished request's usage in."""
        with self._lock:
            model = self._models.pop(run_id, "?")
            for generations in response.generations:
                for generation in generations:
                    message = getattr(generation, "message", None)
                    if (
                        isinstance(generation, ChatGeneration)
                        and isinstance(message, AIMessage)
                        and message.usage_metadata
                    ):
                        self.usage.add(model, dict(message.usage_metadata))


def load_block(data: dict[str, Any]) -> OcrResultBlock:
    """One block of an OcrResult read back from its asdict() JSON."""
    if data["block_type"] == "section":
        return OcrResultSection(
            block_type="section",
            existing_pages=data["existing_pages"],
            block_index=data["block_index"],
            section_content=[load_block(child) for child in data["section_content"]],
        )
    if data["block_type"] == "figure":
        return OcrResultBlockFigure(
            block_type="figure",
            existing_pages=data["existing_pages"],
            block_index=data["block_index"],
            page_index=data["page_index"],
            bounding_box=tuple(data["bounding_box"]),
            caption=data["caption"],
        )
    if data["block_type"] == "table_of_contents":
        return OcrResultBlockTableOfContents(
            block_type="table_of_contents",
            existing_pages=data["existing_pages"],
            block_index=data["block_index"],
            entries=[load_entry(entry) for entry in data["entries"]],
        )
    return OcrResultBlockText(
        block_type=data["block_type"],
        existing_pages=data["existing_pages"],
        block_index=data["block_index"],
        text=data["text"],
    )


def load_entry(data: dict[str, Any]) -> TableOfContentsEntry:
    """One table of contents entry read back from its asdict() JSON, with its children."""
    return TableOfContentsEntry(
        section_number=data["section_number"],
        title=data["title"],
        page_number=data["page_number"],
        children=[load_entry(child) for child in data["children"]],
    )


def load_ocr_result(path: Path) -> OcrResult:
    """An OcrResult read back from the JSON TestMdWriter wrote."""
    data = json.loads(path.read_text(encoding="utf-8"))
    root = load_block(data["root_section"])
    assert isinstance(root, OcrResultSection)
    return OcrResult(root_section=root)


def heading_levels(section: OcrResultSection, depth: int = 0) -> dict[int, int]:
    """The level of every heading of a nested tree: the depth of the section it opens."""
    levels: dict[int, int] = {}

    for block in section.section_content:
        if isinstance(block, OcrResultSection):
            levels.update(heading_levels(block, depth + 1))
        elif isinstance(block, OcrResultBlockText) and block.block_type == "heading":
            levels[block.block_index] = depth

    return levels


def headings_of(section: OcrResultSection) -> list[OcrResultBlockText]:
    """Every heading of a tree, in document order."""
    found: list[OcrResultBlockText] = []

    for block in section.section_content:
        if isinstance(block, OcrResultSection):
            found += headings_of(block)
        elif isinstance(block, OcrResultBlockText) and block.block_type == "heading":
            found.append(block)

    return found


def format_outline(result: OcrResult, truth: dict[int, int] | None) -> str:
    """Every heading indented by its level; marked where the ground truth differs."""
    levels = heading_levels(result.root_section)
    lines = []

    for heading in headings_of(result.root_section):
        level = levels[heading.block_index]
        page = min(heading.existing_pages) + 1 if heading.existing_pages else "-"
        expected = truth.get(heading.block_index) if truth else None
        mark = "" if expected in (None, level) else f"   <-- expected {expected}"
        lines.append(
            f"[{heading.block_index:>4}] p{page:<3} L{level} "
            f"{'  ' * (level - 1)}{heading.text}{mark}"
        )

    return "\n".join(lines)


def nest(levels: list[tuple[int, int]]) -> dict[int, tuple[int | None, int]]:
    """The heading each heading sits directly under, and its depth, by block index.

    Nested as the leveler nests, so a skipped level (1 -> 3) closes up (1 -> 2).
    """
    stack: list[tuple[int, int]] = []
    result: dict[int, tuple[int | None, int]] = {}

    for block_index, level in levels:
        while stack and stack[-1][1] >= level:
            stack.pop()
        result[block_index] = (stack[-1][0] if stack else None, len(stack) + 1)
        stack.append((block_index, level))

    return result


def parents(levels: list[tuple[int, int]]) -> dict[int, int | None]:
    """The heading each heading sits directly under, by block index."""
    return {index: parent for index, (parent, _) in nest(levels).items()}


def score(result: OcrResult, truth: dict[int, int]) -> str:
    """How many levels, and how many parents, match the ground truth."""
    headings = [h.block_index for h in headings_of(result.root_section)]
    levels = heading_levels(result.root_section)
    scored = [index for index in headings if index in truth]

    level_hits = sum(levels[index] == truth[index] for index in scored)
    output_parents = parents([(index, levels[index]) for index in scored])
    truth_parents = parents([(index, truth[index]) for index in scored])
    parent_hits = sum(output_parents[i] == truth_parents[i] for i in scored)

    count = max(len(scored), 1)
    return (
        f"levels:  {level_hits}/{len(scored)} ({level_hits / count:.1%})\n"
        f"parents: {parent_hits}/{len(scored)} ({parent_hits / count:.1%})"
    )


def load_truth(stem: str) -> dict[int, int] | None:
    """The expected depth of every heading, by block index, if written down.

    The ground truth holds the levels as printed; they are closed up into
    depths, as the output tree holds them.
    """
    path = GROUND_TRUTH_DIR / f"{stem}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    levels = sorted((int(index), level) for index, level in data["levels"].items())
    return {index: depth for index, (_, depth) in nest(levels).items()}


def pdf_to_images(pdf_path: Path, dpi: int) -> list[Any]:
    """Every page of the PDF rendered to an RGB PIL image."""
    images = []

    with fitz.open(pdf_path) as document:
        for page in document:
            pixmap = page.get_pixmap(dpi=dpi)
            images.append(
                Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            )

    return images


def run_one(
    stem: str,
    leveler: OcrResultLeveler,
    usage: UsageTotal,
    args: argparse.Namespace,
) -> None:
    """Levels one saved OcrResult and writes the tree, outline, usage and score."""
    print(f"\n=== {stem} ===", flush=True)
    usage.usage = PageUsage()

    ocr_result = load_ocr_result(INPUT_DIR / f"{stem}.json")
    images = pdf_to_images(SAMPLE_DIR / f"{stem}.pdf", args.dpi)
    truth = load_truth(stem)

    started_at = time.monotonic()
    leveled = leveler.level_ocr_result(images, ocr_result)
    elapsed = time.monotonic() - started_at

    output_dir = OUTPUT_DIR / (args.run_name or args.model)
    output_dir.mkdir(parents=True, exist_ok=True)

    outline = format_outline(leveled, truth)
    report = format_report({0: usage.usage})
    scored = score(leveled, truth) if truth else "no ground truth"

    (output_dir / f"{stem}.json").write_text(
        json.dumps(asdict(leveled), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / f"{stem}.outline.txt").write_text(
        f"{outline}\n\n{scored}\n", encoding="utf-8"
    )
    (output_dir / f"{stem}.usage.txt").write_text(
        f"{stem}: {len(headings_of(leveled.root_section))} heading(s) in {elapsed:.1f}s\n{report}\n",
        encoding="utf-8",
    )

    print(outline, flush=True)
    print(f"\n{scored}\ndone in {elapsed:.1f}s -> {output_dir}", flush=True)
    print(report, flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--input",
        action="append",
        help="Stem of an Input/<stem>.json to run. Repeatable. Defaults to every one.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL_ID)
    parser.add_argument("--reasoning-effort", default=None)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI)
    parser.add_argument(
        "--run-name",
        default=None,
        help="Output folder under Output/, to keep variants apart. Defaults to the model id.",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    parser.add_argument("--log-file", default=str(OUTPUT_DIR / "TestLeveler.log"))
    return parser.parse_args()


def configure_logging(log_level: str, log_file: Path) -> None:
    """Writes the leveler's logging to `log_file`, keeping stdout for the outlines."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        filename=log_file,
        filemode="w",
        encoding="utf-8",
    )
    for noisy in ("urllib3", "httpx", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def main() -> int:
    load_dotenv(UPLOADER_ROOT / ".env")
    args = parse_args()
    configure_logging(args.log_level, Path(args.log_file))

    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY is not set.", file=sys.stderr)
        return 1

    from langchain_openai import ChatOpenAI

    stems = args.input or sorted(path.stem for path in INPUT_DIR.glob("*.json"))
    print(f"model: {args.model}")
    print(f"targets: {', '.join(stems)}")
    print(f"log: {args.log_file}")

    usage = UsageTotal()
    leveler = OcrResultLeveler(
        ChatOpenAI(
            model=args.model,
            use_responses_api=True,
            max_tokens=args.max_tokens,
            callbacks=[usage],
            **(
                {"reasoning_effort": args.reasoning_effort}
                if args.reasoning_effort
                else {}
            ),
        )
    )

    failures: list[str] = []
    for stem in stems:
        try:
            run_one(stem, leveler, usage, args)
        except Exception:
            # one bad document should not cost the results of the others
            traceback.print_exc()
            failures.append(stem)

    if failures:
        print(f"\nFAILED: {', '.join(failures)}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
