"""Lets the Pipeline tests import the helpers kept beside them, and gives them a stored document."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PipelineFakes import RecordingObserver, blank_pdf  # noqa: E402

from DataStore.DataStore import DataStore  # noqa: E402
from DataStore.DocumentFiles import DocumentFiles  # noqa: E402


@pytest.fixture
def document(tmp_path: Path) -> DocumentFiles:
    """A stored document of three blank pages."""
    pdf_path = blank_pdf(tmp_path / "three.pdf", 3)
    return DataStore(tmp_path / "Data").import_pdf(pdf_path)


@pytest.fixture
def observer() -> RecordingObserver:
    """An observer with nothing recorded yet."""
    return RecordingObserver()
