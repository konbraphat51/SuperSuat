"""The documents the Uploader works on, each in its own folder under Uploader/Data."""

import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

import fitz  # PyMuPDF

from DataStore.DocumentFiles import DocumentFiles
from DataStore.DocumentMetadata import DocumentMetadata

DEFAULT_DATA_ROOT = Path(__file__).resolve().parents[1] / "Data"
"""Uploader/Data, where the Uploader keeps its files unless told otherwise."""

# A document id as DataStore makes them, so that no id can reach outside the store.
_DOCUMENT_ID = re.compile(r"[0-9a-f]{32}")


class DocumentNotFoundError(LookupError):
    """No document of the given id is in the store."""


class DataStore:
    """Every document of the Uploader, as a DocumentFiles in `<root>/Documents/<id>/`.

    A folder counts as a document once its metadata is written, so a folder an
    import left half-way is never listed.
    """

    def __init__(self, root: Path = DEFAULT_DATA_ROOT) -> None:
        """
        Args:
            root: The folder the store keeps everything in, made when first written.
        """
        self.root = root

    @property
    def documents_dir(self) -> Path:
        """The folder every document's folder is in."""
        return self.root / "Documents"

    def import_pdf(self, pdf_path: Path, name: str | None = None) -> DocumentFiles:
        """Copies a PDF into the store as a new document.

        Args:
            pdf_path: The PDF to import; left where it is.
            name: What to call the document; the PDF's stem if None.

        Raises:
            FileNotFoundError: No file is at `pdf_path`.
            ValueError: The file is not a PDF that can be read.
        """
        if not pdf_path.is_file():
            raise FileNotFoundError(f"No file at {pdf_path}")
        page_count = _count_pdf_pages(pdf_path)

        document = DocumentFiles(self.documents_dir / uuid.uuid4().hex)
        document.directory.mkdir(parents=True)
        try:
            shutil.copyfile(pdf_path, document.source_pdf)
            document.write_metadata(
                DocumentMetadata(
                    document_id=document.document_id,
                    name=name or pdf_path.stem,
                    source_file_name=pdf_path.name,
                    page_count=page_count,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
            )
        except BaseException:
            shutil.rmtree(document.directory, ignore_errors=True)
            raise

        return document

    def open(self, document_id: str) -> DocumentFiles:
        """The document of the given id.

        Raises:
            DocumentNotFoundError: The store holds no such document.
        """
        if not _DOCUMENT_ID.fullmatch(document_id):
            raise DocumentNotFoundError(f"Not a document id: {document_id!r}")

        document = DocumentFiles(self.documents_dir / document_id)
        if not document.metadata_file.is_file():
            raise DocumentNotFoundError(f"No document {document_id}")
        return document

    def list_documents(self) -> list[DocumentFiles]:
        """Every document in the store, the earliest imported first."""
        if not self.documents_dir.is_dir():
            return []

        documents = [
            document
            for document in map(DocumentFiles, self.documents_dir.iterdir())
            if _DOCUMENT_ID.fullmatch(document.document_id)
            and document.metadata_file.is_file()
        ]
        return sorted(
            documents, key=lambda document: document.read_metadata().created_at
        )

    def delete(self, document_id: str) -> None:
        """Removes a document and every file of it.

        Raises:
            DocumentNotFoundError: The store holds no such document.
        """
        document = self.open(document_id)
        # unlisted first, so a delete cut short leaves no half document listed
        document.metadata_file.unlink()
        shutil.rmtree(document.directory)


def _count_pdf_pages(pdf_path: Path) -> int:
    """How many pages the PDF has.

    Raises:
        ValueError: The file is not a PDF that can be read.
    """
    try:
        with fitz.open(pdf_path, filetype="pdf") as document:
            return len(document)
    except RuntimeError as error:  # PyMuPDF's FileDataError among them
        raise ValueError(f"Not a readable PDF: {pdf_path}") from error
