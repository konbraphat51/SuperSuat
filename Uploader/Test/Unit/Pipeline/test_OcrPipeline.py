"""Tests for reading a stored document into its OcrResult."""

from PipelineFakes import RecordingObserver
from PIL.Image import Image

from DataStore.DocumentFiles import DocumentFiles
from OcrModule.Blocked.PageParallel import run_parallel
from OcrModule.MdWriter.Schema import MarkdownDraft
from OcrModule.OcrSchema import OcrResultBlockText, OcrResultSection
from Pipeline.OcrPipeline import OcrPipeline
from Pipeline.Settings import OcrSettings


class FakeWriter:
    """Writes every page as a heading, reporting its progress as MdWriterOcr does."""

    def __init__(self) -> None:
        self.page_sizes: list[tuple[int, int]] = []

    def write_markdown(self, all_page_images: list[Image]) -> MarkdownDraft:
        self.page_sizes = [page.size for page in all_page_images]
        pages = run_parallel(
            lambda index: f"# Page {index}",
            list(range(len(all_page_images))),
            progress_label="writing",
        )
        return MarkdownDraft("\n\n".join(pages), [], list(all_page_images))


def headings_of(section: OcrResultSection) -> list[str]:
    """The text of every heading of a tree, in document order."""
    found: list[str] = []
    for block in section.section_content:
        if isinstance(block, OcrResultSection):
            found += headings_of(block)
        elif isinstance(block, OcrResultBlockText) and block.block_type == "heading":
            found.append(block.text)
    return found


def test_the_result_is_read_and_stored(document: DocumentFiles):
    writer = FakeWriter()
    settings = OcrSettings(dpi=144)

    result = OcrPipeline(settings, lambda _: writer).run(document)

    assert headings_of(result.root_section) == ["Page 0", "Page 1", "Page 2"]
    assert writer.page_sizes == [(144, 144)] * 3
    assert document.read_ocr_result() == result
    assert document.read_ocr_settings() == settings.to_dict()
    assert len(list(document.ocr_pages_dir.iterdir())) == 3


def test_max_pages_reads_only_the_first_pages(document: DocumentFiles):
    writer = FakeWriter()

    OcrPipeline(OcrSettings(max_pages=2), lambda _: writer).run(document)

    assert len(writer.page_sizes) == 2


def test_the_observer_is_told_every_step_and_the_progress(
    document: DocumentFiles, observer: RecordingObserver
):
    OcrPipeline(OcrSettings(), lambda _: FakeWriter(), observer).run(document)

    assert observer.steps == [
        "loading",
        "rendering",
        "transcribing",
        "parsing",
        "saving",
    ]
    assert ("progress", "writing", 3, 3) in observer.events


def test_the_writer_is_built_from_the_settings(document: DocumentFiles):
    built_with: list[OcrSettings] = []
    settings = OcrSettings(model="some-model")

    def factory(given: OcrSettings) -> FakeWriter:
        built_with.append(given)
        return FakeWriter()

    OcrPipeline(settings, factory).run(document)

    assert built_with == [settings]
