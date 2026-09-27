"""An observer remembering what it is told, and the blank PDFs the Pipeline tests read."""

from pathlib import Path

import fitz  # PyMuPDF


class RecordingObserver:
    """Remembers every step and progress it is told of, in order."""

    def __init__(self) -> None:
        self.events: list[tuple[object, ...]] = []

    def step(self, name: str) -> None:
        self.events.append(("step", name))

    def progress(self, label: str, done: int, total: int) -> None:
        self.events.append(("progress", label, done, total))

    @property
    def steps(self) -> list[object]:
        """The names of the steps, in order."""
        return [event[1] for event in self.events if event[0] == "step"]


def blank_pdf(path: Path, page_count: int) -> Path:
    """Writes a PDF of blank pages, each an inch square, to `path`."""
    with fitz.open() as pdf:
        for _ in range(page_count):
            pdf.new_page(width=72, height=72)
        pdf.save(path)
    return path
