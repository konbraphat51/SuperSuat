"""What is known of a stored document from the moment it is imported."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentMetadata:
    """The identity of a stored document and of the PDF it was imported from."""

    document_id: str  # 32 hex digits, naming the document's folder
    name: str  # for people to tell documents apart; the PDF's stem by default
    source_file_name: str  # the PDF's file name as imported
    page_count: int
    created_at: str  # when it was imported, in ISO 8601 with its UTC offset
