"""Nesting a stored document's OcrResult by the level of every heading."""

from collections.abc import Callable, Sequence
from typing import Protocol

from PIL.Image import Image

from DataStore.DocumentFiles import DocumentFiles
from OcrModule.Blocked.PageParallel import listening_progress
from OcrModule.OcrSchema import OcrResult
from Pipeline.PdfPages import LazyPdfPages
from Pipeline.PipelineObserver import PipelineObserver, SilentObserver
from Pipeline.Settings import LevelSettings, OcrSettings


class ResultLeveler(Protocol):
    """Nests a document tree by its heading levels, as OcrResultLeveler does."""

    def level_ocr_result(
        self, all_page_images: Sequence[Image], ocr_result: OcrResult
    ) -> OcrResult:
        """The document tree nested by the level of every heading."""
        ...


class MissingOcrResultError(RuntimeError):
    """The document has not been read by the OCR yet, so has nothing to level."""


class LevelPipeline:
    """Levels the headings of a stored document's OcrResult, and writes the
    nested tree to its files.

    The pages are rendered as the OCR rendered them, so that the page indexes
    of the tree point at the right pages; only the pages the Leveler asks for
    are rendered. Told of in steps: "loading", "leveling", "saving".
    """

    def __init__(
        self,
        settings: LevelSettings,
        leveler_factory: Callable[[LevelSettings], ResultLeveler],
        observer: PipelineObserver | None = None,
    ) -> None:
        """
        Args:
            settings: What the Leveler runs with, stored beside its result.
            leveler_factory: Builds the Leveler out of the settings, such as
                build_leveler; called once per run.
            observer: Told of how a run goes.
        """
        self.settings = settings
        self.leveler_factory = leveler_factory
        self.observer = observer or SilentObserver()

    def run(self, document: DocumentFiles) -> OcrResult:
        """Levels the document's OcrResult, replacing any earlier leveled tree.

        Raises:
            MissingOcrResultError: The OCR has not run over the document.
        """
        if not document.has_result("ocr"):
            raise MissingOcrResultError(
                f"Document {document.document_id} has no OCR result to level"
            )

        self.observer.step("loading")
        leveler = self.leveler_factory(self.settings)
        ocr_result = document.read_ocr_result()
        ocr_settings = OcrSettings.from_dict(document.read_ocr_settings())

        self.observer.step("leveling")
        with (
            LazyPdfPages(
                document.source_pdf, ocr_settings.dpi, ocr_settings.max_pages
            ) as pages,
            listening_progress(self.observer.progress),
        ):
            leveled = leveler.level_ocr_result(pages, ocr_result)

        self.observer.step("saving")
        document.write_level_output(self.settings.to_dict(), leveled)
        return leveled
