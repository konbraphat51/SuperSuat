"""The MdWriter OCR pipeline: find the figures, write the pages out as Markdown, then read it."""

import logging
import time

from PIL.Image import Image

from ..Blocked.Blocker.BlockRenderer import BlockRenderer
from ..Blocked.PageParallel import DEFAULT_MAX_PARALLEL_PAGES, run_parallel
from ..Ocr import Ocr
from ..OcrSchema import OcrResult
from .FigureDetector import FigureDetector
from .MarkdownParser import parse_markdown
from .Schema import DetectedFigure, MarkdownDraft, PageTask
from .Stitcher import stitch
from .Transcriber.PageTranscriber import PageTranscriber

logger = logging.getLogger(__name__)


class MdWriterOcr(Ocr):
    """Reads a document by having a model write it out as Markdown, a page per request.

    A `FigureDetector` finds the figures, which are drawn onto the pages with
    their ids, so the model places each one by id rather than reading it. The
    pages are then written in two passes (see Docs/Plan.md): the pages at
    even indices first, each on its own and all at once, then the pages
    between them, each filling the gap with the Markdown of both neighbours
    in view, so that the parts join into one text. The stitched Markdown is
    last read into the document tree.

    Which models run is the caller's choice: the detector and the transcriber
    are handed in already built."""

    def __init__(
        self,
        figure_detector: FigureDetector,
        transcriber: PageTranscriber,
        max_parallel_pages: int = DEFAULT_MAX_PARALLEL_PAGES,
        renderer: BlockRenderer | None = None,
    ) -> None:
        """
        Args:
            figure_detector: Finds the figures of each page.
            transcriber: Writes a page out as Markdown.
            max_parallel_pages: Most pages sent to the model at once.
            renderer: Draws the figures and their ids onto the pages.
        """
        self.figure_detector = figure_detector
        self.transcriber = transcriber
        self.max_parallel_pages = max_parallel_pages
        self.renderer = renderer or BlockRenderer()

    def ocr(
        self,
        all_page_images: list[Image],
    ) -> OcrResult:
        """Reads every page, in order, into a single document tree."""
        draft = self.write_markdown(all_page_images)
        return parse_markdown(draft.markdown, draft.figures)

    def write_markdown(self, all_page_images: list[Image]) -> MarkdownDraft:
        """Every page written out as one Markdown document, not yet parsed."""
        logger.info("MdWriter OCR | %d page(s)", len(all_page_images))
        tasks = [PageTask(page_index) for page_index in range(len(all_page_images))]

        figures = self.figure_detector.detect(all_page_images)
        rendered_pages = self._render(all_page_images, figures)

        written = self._write(tasks, rendered_pages, figures)
        filled = self._fill(tasks, rendered_pages, figures, written)

        markdowns = {**written, **filled}
        markdown = stitch([(task, markdowns[task.page_index]) for task in tasks])
        return MarkdownDraft(
            markdown=markdown, figures=figures, rendered_pages=rendered_pages
        )

    def _render(
        self,
        pages: list[Image],
        figures: list[DetectedFigure],
    ) -> list[Image]:
        """Every page with its figures' boxes and ids drawn on."""
        return [
            self.renderer.render_page(
                page, [figure for figure in figures if figure.page_index == index]
            )
            for index, page in enumerate(pages)
        ]

    def _write(
        self,
        tasks: list[PageTask],
        rendered_pages: list[Image],
        figures: list[DetectedFigure],
    ) -> dict[int, str]:
        """The first pass: the Markdown of every write page, by page index."""
        write_tasks = [task for task in tasks if task.kind == "write"]
        started_at = time.monotonic()

        markdowns = run_parallel(
            lambda task: self.transcriber.write(task, rendered_pages, figures),
            write_tasks,
            self.max_parallel_pages,
            progress_label="writing",
        )
        logger.info(
            "write pass | %d page(s) in %.1fs",
            len(write_tasks),
            time.monotonic() - started_at,
        )
        return {task.page_index: md for task, md in zip(write_tasks, markdowns)}

    def _fill(
        self,
        tasks: list[PageTask],
        rendered_pages: list[Image],
        figures: list[DetectedFigure],
        written: dict[int, str],
    ) -> dict[int, str]:
        """The second pass: the Markdown of every fill page, by page index,
        each written against the write pages either side of it."""
        fill_tasks = [task for task in tasks if task.kind == "fill"]
        started_at = time.monotonic()

        markdowns = run_parallel(
            lambda task: self.transcriber.fill(
                task,
                rendered_pages,
                figures,
                previous_markdown=written[task.page_index - 1],
                next_markdown=written.get(task.page_index + 1),
            ),
            fill_tasks,
            self.max_parallel_pages,
            progress_label="filling",
        )
        logger.info(
            "fill pass | %d page(s) in %.1fs",
            len(fill_tasks),
            time.monotonic() - started_at,
        )
        return {task.page_index: md for task, md in zip(fill_tasks, markdowns)}
