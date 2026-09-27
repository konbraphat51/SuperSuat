"""Tests for nesting a stored document's OcrResult by its heading levels."""

from collections.abc import Sequence

import pytest
from PIL import Image as PilImage
from PIL.Image import Image
from PipelineFakes import RecordingObserver

from DataStore.DocumentFiles import DocumentFiles
from OcrModule.OcrSchema import OcrResult, OcrResultBlockText, OcrResultSection
from Pipeline.LevelPipeline import LevelPipeline, MissingOcrResultError
from Pipeline.Settings import LevelSettings, OcrSettings


def flat_result() -> OcrResult:
    """A tree of one heading, not nested."""
    heading = OcrResultBlockText("heading", [2], 1, "Chapter")
    return OcrResult(OcrResultSection("section", [2], 0, [heading]))


def nested_result() -> OcrResult:
    """The tree of flat_result, its heading opening a section."""
    heading = OcrResultBlockText("heading", [2], 1, "Chapter")
    chapter = OcrResultSection("section", [2], 2, [heading])
    return OcrResult(OcrResultSection("section", [2], 0, [chapter]))


class FakeLeveler:
    """Nests every tree as nested_result, remembering the pages it was given."""

    def __init__(self) -> None:
        self.page_count = 0
        self.page_size: tuple[int, int] | None = None
        self.given: OcrResult | None = None

    def level_ocr_result(
        self, all_page_images: Sequence[Image], ocr_result: OcrResult
    ) -> OcrResult:
        self.page_count = len(all_page_images)
        self.page_size = all_page_images[2].size
        self.given = ocr_result
        return nested_result()


def read_by_ocr(document: DocumentFiles, settings: OcrSettings) -> None:
    """Stores flat_result as the document's OCR result, read with `settings`."""
    page = PilImage.new("RGB", (4, 4))
    document.write_ocr_output(settings.to_dict(), "# Chapter", flat_result(), [page])


def test_the_ocr_result_is_leveled_and_stored(document: DocumentFiles):
    read_by_ocr(document, OcrSettings())
    leveler = FakeLeveler()
    settings = LevelSettings(model="some-model")

    result = LevelPipeline(settings, lambda _: leveler).run(document)

    assert leveler.given == flat_result()
    assert result == nested_result()
    assert document.read_level_result() == nested_result()
    assert document.read_level_settings() == settings.to_dict()


def test_the_pages_are_rendered_as_the_ocr_rendered_them(document: DocumentFiles):
    read_by_ocr(document, OcrSettings(dpi=144, max_pages=3))
    leveler = FakeLeveler()

    LevelPipeline(LevelSettings(), lambda _: leveler).run(document)

    assert leveler.page_count == 3
    assert leveler.page_size == (144, 144)


def test_a_document_the_ocr_has_not_read_is_refused(document: DocumentFiles):
    with pytest.raises(MissingOcrResultError):
        LevelPipeline(LevelSettings(), lambda _: FakeLeveler()).run(document)


def test_the_observer_is_told_every_step(
    document: DocumentFiles, observer: RecordingObserver
):
    read_by_ocr(document, OcrSettings())

    LevelPipeline(LevelSettings(), lambda _: FakeLeveler(), observer).run(document)

    assert observer.steps == ["loading", "leveling", "saving"]
