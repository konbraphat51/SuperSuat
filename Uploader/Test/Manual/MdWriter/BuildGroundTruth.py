"""Extracting the ground truth of a born-digital sample PDF from its text layer.

Writes `GroundTruth/<stem>/page_<N>.txt` for every page, for Evaluate.py to
score a run against. Only for a PDF with a text layer; the scanned samples
have hand-written ground truth instead.

The Japanese fonts of Seaman.pdf carry a broken ToUnicode map, so their glyphs
are decoded from the Adobe-Japan1 character collection instead. Text the
pipeline is told to leave out is left out here too: the running head at the
top of each page, and anything inside a detected figure box.

Usage (from the `Uploader` directory):

    uv run python Test/Manual/MdWriter/BuildGroundTruth.py --pdf Seaman.pdf \
        --figures Test/Manual/MdWriter/Output/yomitoku/gpt-6-sol/Seaman.json
"""

import argparse
import json
from pathlib import Path
from typing import Any

from pdfminer.cmapdb import CMapDB
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTChar, LTPage, LTTextBox, LTTextLine
from pdfminer.pdffont import PDFCIDFont
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage

MANUAL_DIR = Path(__file__).resolve().parent
SAMPLE_DIR = MANUAL_DIR.parents[1] / "Manual" / "Ocr" / "Sample"
GROUND_TRUTH_DIR = MANUAL_DIR / "GroundTruth"

# Share of the page height at the top that holds the running head.
RUNNING_HEAD_SHARE = 0.07

# The resolution the figure boxes were detected at, as the manual run renders.
DETECTION_DPI = 200

# Points per inch, the unit of PDF coordinates.
POINTS_PER_INCH = 72

# The columns of the journal's body text.
COLUMN_COUNT = 3

# How much wider than a column a line is, at least, to span the columns.
SPANNING_SHARE = 1.3


def use_adobe_japan1_for_cid_fonts() -> None:
    """Decodes every Adobe-Japan1 CID font by its collection, not its ToUnicode map."""
    original = PDFCIDFont.to_unichr
    collection = CMapDB.get_unicode_map("Adobe-Japan1", False)

    def to_unichr(self: PDFCIDFont, cid: int) -> str:
        if self.cidcoding == "Adobe-Japan1":
            try:
                return collection.get_unichr(cid)
            except KeyError:
                pass
        return original(self, cid)

    PDFCIDFont.to_unichr = to_unichr  # type: ignore[method-assign]


def figure_boxes(figures_json: Path | None) -> dict[int, list[tuple[float, ...]]]:
    """The figure boxes of a run's document tree, by page, in PDF points."""
    if figures_json is None:
        return {}

    scale = POINTS_PER_INCH / DETECTION_DPI
    boxes: dict[int, list[tuple[float, ...]]] = {}

    def visit(section: dict[str, Any]) -> None:
        for block in section["section_content"]:
            if block["block_type"] == "section":
                visit(block)
            elif block["block_type"] == "figure":
                x, y, w, h = block["bounding_box"]
                boxes.setdefault(block["page_index"], []).append(
                    (x * scale, y * scale, (x + w) * scale, (y + h) * scale)
                )

    visit(json.loads(figures_json.read_text(encoding="utf-8"))["root_section"])
    return boxes


def page_text(layout: LTPage, boxes: list[tuple[float, ...]]) -> str:
    """The page's text, box by box, without its running head or figure text."""
    height = layout.height
    head_bottom = height * (1 - RUNNING_HEAD_SHARE)

    def kept(char: LTChar) -> bool:
        # pdfminer measures y from the bottom; the boxes measure it from the top
        top = height - char.y1
        centre_x, centre_y = (char.x0 + char.x1) / 2, top + (char.y1 - char.y0) / 2
        in_figure = any(
            x0 <= centre_x <= x1 and y0 <= centre_y <= y1 for x0, y0, x1, y1 in boxes
        )
        return char.y0 < head_bottom and not in_figure

    lines = [
        line
        for element in layout
        if isinstance(element, LTTextBox)
        for line in element
        if isinstance(line, LTTextLine)
    ]
    texts = [
        "".join(
            char.get_text() for char in line if isinstance(char, LTChar) and kept(char)
        ).strip()
        for line in _reading_order(lines, layout.width)
    ]
    return "\n".join(text for text in texts if text) + "\n"


def _reading_order(lines: list[LTTextLine], page_width: float) -> list[LTTextLine]:
    """The lines of a multi-column page in reading order.

    A line wider than a column cuts the page into bands; within a band, the
    columns, told apart by where a line is centred, are read left to right,
    each from top to bottom.
    """
    column_width = page_width / COLUMN_COUNT
    top_down = sorted(lines, key=lambda line: -line.y1)
    ordered: list[LTTextLine] = []
    band: list[LTTextLine] = []

    def flush() -> None:
        band.sort(
            key=lambda line: (int((line.x0 + line.x1) / 2 // column_width), -line.y1)
        )
        ordered.extend(band)
        band.clear()

    for line in top_down:
        if line.width > column_width * SPANNING_SHARE:
            flush()
            ordered.append(line)
        else:
            band.append(line)

    flush()
    return ordered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--figures", type=Path, default=None)
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.is_file():
        pdf_path = SAMPLE_DIR / args.pdf

    use_adobe_japan1_for_cid_fonts()
    boxes = figure_boxes(args.figures)
    output_dir = GROUND_TRUTH_DIR / pdf_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    resources = PDFResourceManager()
    device = PDFPageAggregator(resources, laparams=LAParams())
    interpreter = PDFPageInterpreter(resources, device)

    with pdf_path.open("rb") as file:
        for page_index, page in enumerate(PDFPage.get_pages(file)):
            interpreter.process_page(page)
            text = page_text(device.get_result(), boxes.get(page_index, []))
            (output_dir / f"page_{page_index}.txt").write_text(text, encoding="utf-8")
            print(f"page {page_index}: {len(text)} characters")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
