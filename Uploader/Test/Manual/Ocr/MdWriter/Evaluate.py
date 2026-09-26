"""Scoring the Markdown of manual runs against the ground truth, page by page.

For every PDF that has `GroundTruth/<stem>/page_<N>.txt`, reads `<stem>.md` from
each run directory, splits it at its page markers, and compares every page
with its ground truth. Both sides are first reduced to their letters and
digits, so that Markdown syntax, punctuation, spacing and line breaks do not
count; LaTeX is reduced the same way, its Greek letters and function names
kept.

- CER: the edit distance over the ground truth's length. Reading order counts.
- Precision: the share of the output's character bigrams found in the ground
  truth. Low when the model invents or repeats text.
- Recall: the share of the ground truth's bigrams found in the output. Low when
  the model leaves text out.

Usage (from the `Uploader` directory):

    uv run python Test/Manual/Ocr/MdWriter/Evaluate.py \
        Test/Manual/Ocr/MdWriter/Output/yomitoku/gpt-6-luna \
        Test/Manual/Ocr/MdWriter/Output/yomitoku/gpt-6-sol
"""

import argparse
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from rapidfuzz.distance import Levenshtein

GROUND_TRUTH_DIR = Path(__file__).resolve().parent / "GroundTruth"

# A page marker, which the stitcher put where each page starts.
PAGE_MARKER = re.compile(r"<!--\s*page:\s*(\d+)\s*-->")

# Any other HTML comment, as the continuation markers.
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)

# A placed figure, whose alt text is the caption printed on the page.
FIGURE = re.compile(r"!\[([^\]]*)\]\(\s*figure:\d+\s*\)")

# LaTeX commands kept as the letters they are printed as.
LATEX_SYMBOLS = {
    "alpha": "α",
    "beta": "β",
    "gamma": "γ",
    "delta": "δ",
    "epsilon": "ε",
    "theta": "θ",
    "lambda": "λ",
    "mu": "μ",
    "pi": "π",
    "sigma": "σ",
    "phi": "φ",
    "omega": "ω",
    "sin": "sin",
    "cos": "cos",
    "tan": "tan",
    "log": "log",
    "lim": "lim",
}

# A LaTeX command, as `\alpha` or `\frac`.
LATEX_COMMAND = re.compile(r"\\([A-Za-z]+)")


@dataclass
class Score:
    """How far one run's text is from the ground truth.

    Attributes:
        distance: The edit distance between the two.
        truth_length: How many characters the ground truth has.
        matched_bigrams: Character bigrams the two have in common.
        output_bigrams: Character bigrams of the output.
        truth_bigrams: Character bigrams of the ground truth.
    """

    distance: int = 0
    truth_length: int = 0
    matched_bigrams: int = 0
    output_bigrams: int = 0
    truth_bigrams: int = 0

    def add(self, other: "Score") -> None:
        """Counts another score in, for the totals."""
        self.distance += other.distance
        self.truth_length += other.truth_length
        self.matched_bigrams += other.matched_bigrams
        self.output_bigrams += other.output_bigrams
        self.truth_bigrams += other.truth_bigrams

    @property
    def cer(self) -> float:
        """The character error rate."""
        return self.distance / max(self.truth_length, 1)

    @property
    def precision(self) -> float:
        """The share of the output's bigrams that are in the ground truth."""
        return self.matched_bigrams / max(self.output_bigrams, 1)

    @property
    def recall(self) -> float:
        """The share of the ground truth's bigrams that are in the output."""
        return self.matched_bigrams / max(self.truth_bigrams, 1)


def normalize(text: str) -> str:
    """The text reduced to its letters and digits, Markdown and LaTeX taken out."""
    text = FIGURE.sub(r"\1", COMMENT.sub("", text))
    text = LATEX_COMMAND.sub(lambda m: LATEX_SYMBOLS.get(m.group(1), ""), text)
    text = unicodedata.normalize("NFKC", text)
    return "".join(ch for ch in text if unicodedata.category(ch)[0] in "LN")


def score(output: str, truth: str) -> Score:
    """How far the output is from the ground truth, both normalized."""
    output_bigrams = Counter(output[i : i + 2] for i in range(len(output) - 1))
    truth_bigrams = Counter(truth[i : i + 2] for i in range(len(truth) - 1))

    return Score(
        distance=Levenshtein.distance(output, truth),
        truth_length=len(truth),
        matched_bigrams=sum((output_bigrams & truth_bigrams).values()),
        output_bigrams=sum(output_bigrams.values()),
        truth_bigrams=sum(truth_bigrams.values()),
    )


def split_pages(markdown: str) -> dict[int, str]:
    """The Markdown of every page, cut at the page markers."""
    pages: dict[int, str] = {}
    current = 0

    for index, chunk in enumerate(PAGE_MARKER.split(markdown)):
        if index % 2:
            current = int(chunk)
        else:
            pages[current] = pages.get(current, "") + chunk

    return pages


def evaluate_run(run_dir: Path) -> dict[str, dict[int, Score]]:
    """Every scored page of a run, by PDF and page."""
    results: dict[str, dict[int, Score]] = {}

    for truth_dir in sorted(GROUND_TRUTH_DIR.iterdir()):
        markdown_path = run_dir / f"{truth_dir.name}.md"
        if not truth_dir.is_dir() or not markdown_path.is_file():
            continue

        pages = split_pages(markdown_path.read_text(encoding="utf-8"))
        results[truth_dir.name] = {}

        for truth_path in sorted(truth_dir.glob("page_*.txt")):
            page_index = int(truth_path.stem.removeprefix("page_"))
            truth = normalize(truth_path.read_text(encoding="utf-8"))
            output = normalize(pages.get(page_index, ""))
            results[truth_dir.name][page_index] = score(output, truth)

    return results


def format_row(label: str, value: Score) -> str:
    """One line of the table."""
    return (
        f"{label:<24} {value.cer:>6.3f} {value.precision:>6.3f} "
        f"{value.recall:>6.3f} {value.truth_length:>6}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("runs", nargs="+", type=Path, help="Run output directories")
    parser.add_argument(
        "--pages", action="store_true", help="Show every page, not only the totals"
    )
    args = parser.parse_args()

    header = f"{'':<24} {'CER':>6} {'prec':>6} {'recall':>6} {'chars':>6}"
    for run_dir in args.runs:
        if not run_dir.is_dir():
            print(f"not a directory: {run_dir}", file=sys.stderr)
            return 1

        results = evaluate_run(run_dir)
        total = Score()
        print(f"\n## {run_dir}\n{header}")

        for stem, pages in results.items():
            document = Score()
            for page_index, value in pages.items():
                document.add(value)
                if args.pages:
                    print(format_row(f"  {stem} p{page_index}", value))
            total.add(document)
            print(format_row(stem, document))

        print(format_row("all", total))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
