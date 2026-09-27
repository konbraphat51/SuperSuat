"""A stored document as the commands tell of it, in plain JSON values."""

from dataclasses import asdict
from typing import Any, get_args

from DataStore.DocumentFiles import DocumentFiles, Stage

_STAGES: tuple[Stage, ...] = get_args(Stage)


def describe_document(document: DocumentFiles) -> dict[str, Any]:
    """The document's metadata, where its files are, and how far each stage has run.

    Every path is absolute, so that the GUI can read the files it names.
    """
    return {
        **asdict(document.read_metadata()),
        "directory": str(document.directory.resolve()),
        "source_pdf": str(document.source_pdf.resolve()),
        "stages": {stage: _describe_stage(document, stage) for stage in _STAGES},
    }


def _describe_stage(document: DocumentFiles, stage: Stage) -> dict[str, Any]:
    """Whether a stage has run to the end, what it ran with, and where its files are."""
    done = document.has_result(stage)

    if stage == "ocr":
        files = {
            "result_file": document.ocr_result_file,
            "markdown_file": document.ocr_markdown_file,
            "pages_dir": document.ocr_pages_dir,
        }
        settings = document.read_ocr_settings() if done else None
    else:
        files = {"result_file": document.level_result_file}
        settings = document.read_level_settings() if done else None

    return {
        "done": done,
        "settings": settings,
        **{name: str(path.resolve()) for name, path in files.items()},
        "log_file": str(document.log_file(stage).resolve()),
    }
