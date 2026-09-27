"""Tests for the store of every document's files."""

from pathlib import Path

import fitz  # PyMuPDF
import pytest
from PIL import Image

from DataStore.DataStore import DataStore, DocumentNotFoundError
from OcrModule.OcrSchema import OcrResult, OcrResultBlockText, OcrResultSection


@pytest.fixture
def store(tmp_path: Path) -> DataStore:
    """An empty store in a folder of its own."""
    return DataStore(tmp_path / "Data")


@pytest.fixture
def pdf_path(tmp_path: Path) -> Path:
    """A PDF of two blank pages."""
    path = tmp_path / "Sample Book.pdf"
    with fitz.open() as document:
        document.new_page()
        document.new_page()
        document.save(path)
    return path


def result_of(text: str) -> OcrResult:
    """A tree of one paragraph."""
    paragraph = OcrResultBlockText("paragraph", [0], 1, text)
    return OcrResult(OcrResultSection("section", [0], 0, [paragraph]))


def test_an_imported_pdf_is_copied_in_with_its_metadata(
    store: DataStore, pdf_path: Path
):
    document = store.import_pdf(pdf_path)

    metadata = document.read_metadata()
    assert document.source_pdf.read_bytes() == pdf_path.read_bytes()
    assert document.directory.parent == store.documents_dir
    assert metadata.document_id == document.document_id
    assert metadata.name == "Sample Book"
    assert metadata.source_file_name == "Sample Book.pdf"
    assert metadata.page_count == 2


def test_an_import_may_name_the_document(store: DataStore, pdf_path: Path):
    document = store.import_pdf(pdf_path, name="Probability")

    assert document.read_metadata().name == "Probability"


def test_a_file_that_is_not_a_pdf_is_refused_and_leaves_nothing(
    store: DataStore, tmp_path: Path
):
    not_pdf = tmp_path / "notes.pdf"
    not_pdf.write_text("hello", encoding="utf-8")

    with pytest.raises(ValueError, match="Not a readable PDF"):
        store.import_pdf(not_pdf)
    assert store.list_documents() == []


def test_a_missing_file_is_refused(store: DataStore, tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        store.import_pdf(tmp_path / "missing.pdf")


def test_documents_are_listed_the_earliest_imported_first(
    store: DataStore, pdf_path: Path
):
    first = store.import_pdf(pdf_path, name="first")
    second = store.import_pdf(pdf_path, name="second")

    listed = [document.document_id for document in store.list_documents()]

    assert listed == [first.document_id, second.document_id]


def test_a_folder_without_metadata_is_not_listed(store: DataStore, pdf_path: Path):
    document = store.import_pdf(pdf_path)
    document.metadata_file.unlink()

    assert store.list_documents() == []


def test_a_document_is_opened_by_its_id(store: DataStore, pdf_path: Path):
    document = store.import_pdf(pdf_path)

    assert store.open(document.document_id).directory == document.directory


@pytest.mark.parametrize("document_id", ["0" * 32, "..", "../Data", "ABC"])
def test_an_unknown_or_malformed_id_is_not_found(store: DataStore, document_id: str):
    with pytest.raises(DocumentNotFoundError):
        store.open(document_id)


def test_a_deleted_document_is_gone(store: DataStore, pdf_path: Path):
    document = store.import_pdf(pdf_path)

    store.delete(document.document_id)

    assert not document.directory.exists()
    with pytest.raises(DocumentNotFoundError):
        store.open(document.document_id)


def test_the_ocr_output_reads_back(store: DataStore, pdf_path: Path):
    document = store.import_pdf(pdf_path)
    page = Image.new("RGB", (4, 4))

    document.write_ocr_output({"dpi": 200}, "text", result_of("text"), [page, page])

    assert document.has_result("ocr")
    assert document.read_ocr_settings() == {"dpi": 200}
    assert document.read_ocr_result() == result_of("text")
    assert document.ocr_markdown_file.read_text(encoding="utf-8") == "text"
    assert sorted(path.name for path in document.ocr_pages_dir.iterdir()) == [
        "page_0.png",
        "page_1.png",
    ]


def test_the_level_output_reads_back(store: DataStore, pdf_path: Path):
    document = store.import_pdf(pdf_path)

    document.write_level_output({"model": "m"}, result_of("leveled"))

    assert document.has_result("level")
    assert document.read_level_settings() == {"model": "m"}
    assert document.read_level_result() == result_of("leveled")


def test_a_new_ocr_run_drops_the_earlier_one_and_its_leveled_tree(
    store: DataStore, pdf_path: Path
):
    document = store.import_pdf(pdf_path)
    page = Image.new("RGB", (4, 4))
    document.write_ocr_output({}, "old", result_of("old"), [page, page])
    document.write_level_output({}, result_of("old"))

    document.write_ocr_output({}, "new", result_of("new"), [page])

    assert document.read_ocr_result() == result_of("new")
    assert [path.name for path in document.ocr_pages_dir.iterdir()] == ["page_0.png"]
    assert not document.has_result("level")


def test_nothing_has_run_over_a_new_document(store: DataStore, pdf_path: Path):
    document = store.import_pdf(pdf_path)

    assert not document.has_result("ocr")
    assert not document.has_result("level")
