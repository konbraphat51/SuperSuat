"""The LinearMD OCR pipeline: find the figures, write the pages out as Markdown, then read it."""

import logging

from PIL.Image import Image

from ..Blocked.Blocker.BlockRenderer import BlockRenderer
from ..Blocked.PageParallel import DEFAULT_MAX_PARALLEL_PAGES, run_parallel
from ..Ocr import Ocr
from ..OcrSchema import OcrResult
from .Batching import plan_batches
from .FigureDetector import FigureDetector
from .MarkdownParser import parse_markdown
from .Schema import DetectedFigure, MarkdownDraft, PageBatch
from .Stitcher import stitch
from .Transcriber.BatchTranscriber import BatchTranscriber

logger = logging.getLogger(__name__)

# Pages apart the batches start; each request carries one page more than this.
DEFAULT_BATCH_SIZE = 4


class LinearMdOcr(Ocr):
    """Reads a document by having a model write whole runs of pages as Markdown.

    A `FigureDetector` finds the figures, which are drawn onto the pages with
    their ids, so the model places each one by id rather than reading it. The
    pages are then written in overlapping batches (see Docs/Plan.md): the even
    batches first, all at once, then the odd batches, each filling the gap
    between two even ones with both of them in view, so that the parts join
    into one text. The stitched Markdown is last read into the document tree.

    Which models run is the caller's choice: the detector and the transcriber
    are handed in already built."""

    def __init__(
        self,
        figure_detector: FigureDetector,
        transcriber: BatchTranscriber,
        batch_size: int = DEFAULT_BATCH_SIZE,
        max_parallel_batches: int = DEFAULT_MAX_PARALLEL_PAGES,
        renderer: BlockRenderer | None = None,
    ) -> None:
        """
        Args:
            figure_detector: Finds the figures of each page.
            transcriber: Writes a batch of pages out as Markdown.
            batch_size: Pages apart the batches start; at least 2.
            max_parallel_batches: Most batches sent to the model at once.
            renderer: Draws the figures and their ids onto the pages.
        """
        self.figure_detector = figure_detector
        self.transcriber = transcriber
        self.batch_size = batch_size
        self.max_parallel_batches = max_parallel_batches
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
        logger.info("LinearMD OCR | %d page(s)", len(all_page_images))
        batches = plan_batches(len(all_page_images), self.batch_size)

        figures = self.figure_detector.detect(all_page_images)
        rendered_pages = self._render(all_page_images, figures)

        written = self._write(batches, rendered_pages, figures)
        filled = self._fill(batches, rendered_pages, figures, written)

        markdown = stitch(
            [(batch, {**written, **filled}[batch.index]) for batch in batches]
        )
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
        batches: list[PageBatch],
        rendered_pages: list[Image],
        figures: list[DetectedFigure],
    ) -> dict[int, str]:
        """The first pass: the Markdown of every even batch, by batch index."""
        write_batches = [batch for batch in batches if batch.kind == "write"]

        markdowns = run_parallel(
            lambda batch: self.transcriber.write(batch, rendered_pages, figures),
            write_batches,
            self.max_parallel_batches,
            progress_label="writing",
            progress_unit="batch",
        )
        return {batch.index: md for batch, md in zip(write_batches, markdowns)}

    def _fill(
        self,
        batches: list[PageBatch],
        rendered_pages: list[Image],
        figures: list[DetectedFigure],
        written: dict[int, str],
    ) -> dict[int, str]:
        """The second pass: the Markdown of every odd batch, by batch index,
        each written against the even batches either side of it."""
        fill_batches = [batch for batch in batches if batch.kind == "fill"]

        markdowns = run_parallel(
            lambda batch: self.transcriber.fill(
                batch,
                rendered_pages,
                figures,
                previous_markdown=written[batch.index - 1],
                next_markdown=written.get(batch.index + 1),
            ),
            fill_batches,
            self.max_parallel_batches,
            progress_label="filling",
            progress_unit="batch",
        )
        return {batch.index: md for batch, md in zip(fill_batches, markdowns)}
