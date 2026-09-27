"""Reading a stored document's PDF into its OcrResult."""

from collections.abc import Callable
from typing import Protocol

from PIL.Image import Image

from DataStore.DocumentFiles import DocumentFiles
from OcrModule.Blocked.PageParallel import listening_progress
from OcrModule.MdWriter.Parser.MarkdownParser import parse_markdown
from OcrModule.MdWriter.Schema import MarkdownDraft
from OcrModule.OcrSchema import OcrResult
from Pipeline.PdfPages import LazyPdfPages
from Pipeline.PipelineObserver import PipelineObserver, SilentObserver
from Pipeline.Settings import OcrSettings


class MarkdownWriter(Protocol):
    """Writes the pages of a document out as Markdown, as MdWriterOcr does."""

    def write_markdown(self, all_page_images: list[Image]) -> MarkdownDraft:
        """Every page written out as one Markdown document, not yet parsed."""
        ...


class OcrPipeline:
    """Reads a stored document's PDF with the MdWriter OCR, and writes the
    Markdown, the OcrResult and the pages as the model saw them to its files.

    Told of in steps: "loading", "rendering", "transcribing", "parsing",
    "saving"; the transcription also reports its labelled stages' progress.
    """

    def __init__(
        self,
        settings: OcrSettings,
        writer_factory: Callable[[OcrSettings], MarkdownWriter],
        observer: PipelineObserver | None = None,
    ) -> None:
        """
        Args:
            settings: What the OCR runs with, stored beside its result.
            writer_factory: Builds the OCR out of the settings, such as
                build_md_writer_ocr; called once per run.
            observer: Told of how a run goes.
        """
        self.settings = settings
        self.writer_factory = writer_factory
        self.observer = observer or SilentObserver()

    def run(self, document: DocumentFiles) -> OcrResult:
        """Reads the document, replacing any earlier OCR of it and its leveled tree."""
        self.observer.step("loading")
        writer = self.writer_factory(self.settings)

        self.observer.step("rendering")
        with LazyPdfPages(
            document.source_pdf, self.settings.dpi, self.settings.max_pages
        ) as pages:
            images = list(pages)

        self.observer.step("transcribing")
        with listening_progress(self.observer.progress):
            draft = writer.write_markdown(images)

        self.observer.step("parsing")
        result = parse_markdown(draft.markdown, draft.figures)

        self.observer.step("saving")
        document.write_ocr_output(
            self.settings.to_dict(), draft.markdown, result, draft.rendered_pages
        )
        return result
