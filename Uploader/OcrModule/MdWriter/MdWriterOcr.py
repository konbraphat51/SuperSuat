"""The MdWriter OCR pipeline: find the figures, write the pages out as Markdown, then read it."""

import logging
import time

from PIL.Image import Image

from ..Blocked.Blocker.BlockRenderer import BlockRenderer
from ..Blocked.PageParallel import DEFAULT_MAX_PARALLEL_PAGES, run_parallel
from ..Ocr import Ocr
from ..OcrSchema import OcrResult
from .FigureDetector import FigureDetector
from .Markers import split_continuation
from .MarkdownParser import parse_markdown
from .PageJoin import JoinJudge, decide_joins
from .Schema import DetectedFigure, MarkdownDraft, PageTask
from .Stitcher import stitch
from .Transcriber.PageTranscriber import PageTranscriber

logger = logging.getLogger(__name__)


class MdWriterOcr(Ocr):
    """Reads a document by having a model write it out as Markdown, a page per request.

    A `FigureDetector` finds the figures, which are drawn onto the pages with
    their ids, so the model places each one by id rather than reading it.
    Every page is then written at once, each on its own (see Docs/Plan.md),
    saying of its own ends whether its text runs over the page turn; where
    two pages disagree, a `JoinJudge` settles it. The stitched Markdown is
    last read into the document tree.

    Which models run is the caller's choice: the detector, the transcriber
    and the judge are handed in already built."""

    def __init__(
        self,
        figure_detector: FigureDetector,
        transcriber: PageTranscriber,
        join_judge: JoinJudge | None = None,
        max_parallel_pages: int = DEFAULT_MAX_PARALLEL_PAGES,
        renderer: BlockRenderer | None = None,
    ) -> None:
        """
        Args:
            figure_detector: Finds the figures of each page.
            transcriber: Writes a page out as Markdown.
            join_judge: Settles a page turn the two pages disagree on; without
                one, whether the paragraph stops at a sentence's end does.
            max_parallel_pages: Most pages sent to the model at once.
            renderer: Draws the figures and their ids onto the pages.
        """
        self.figure_detector = figure_detector
        self.transcriber = transcriber
        self.join_judge = join_judge
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
        page_count = len(all_page_images)
        logger.info("MdWriter OCR | %d page(s)", page_count)
        tasks = [PageTask(index, page_count) for index in range(page_count)]

        figures = self.figure_detector.detect(all_page_images)
        rendered_pages = self._render(all_page_images, figures)

        pages = [
            split_continuation(markdown)
            for markdown in self._write(tasks, rendered_pages, figures)
        ]
        joins = decide_joins(pages, self.join_judge)

        markdown = stitch([page.body for page in pages], joins)
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
    ) -> list[str]:
        """The Markdown of every page, in page order."""
        started_at = time.monotonic()

        markdowns = run_parallel(
            lambda task: self.transcriber.transcribe(task, rendered_pages, figures),
            tasks,
            self.max_parallel_pages,
            progress_label="writing",
        )
        logger.info(
            "write | %d page(s) in %.1fs", len(tasks), time.monotonic() - started_at
        )
        return markdowns
