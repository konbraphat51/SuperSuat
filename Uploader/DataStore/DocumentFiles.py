"""The files of one stored document, and reading and writing them.

Laid out as:

    <document_id>/
        document.json       DocumentMetadata
        source.pdf          the PDF as imported
        ocr/
            settings.json   what the OCR ran with
            draft.md        the Markdown the model wrote
            result.json     the OcrResult
            pages/page_<N>.png   every page as the model saw it, figures boxed
        level/
            settings.json   what the Leveler ran with
            result.json     the OcrResult nested by heading level
        logs/<stage>.log    the logging of the last run of each stage
"""

import json
import os
import shutil
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal

from PIL.Image import Image

from DataStore.DocumentMetadata import DocumentMetadata
from OcrModule.OcrResultJson import dump_ocr_result, load_ocr_result
from OcrModule.OcrSchema import OcrResult

Stage = Literal["ocr", "level"]
"""A pipeline run over a document, in the order they run."""


class DocumentFiles:
    """The files of one stored document, in its own folder.

    A stage's result is written last and atomically, so a stage counts as done
    exactly when its result file exists, even if a run was killed mid-way.
    """

    def __init__(self, directory: Path) -> None:
        """
        Args:
            directory: The document's folder, which DataStore names by its id.
        """
        self.directory = directory

    @property
    def document_id(self) -> str:
        """The id of the document, which its folder is named by."""
        return self.directory.name

    @property
    def metadata_file(self) -> Path:
        """The DocumentMetadata, as JSON."""
        return self.directory / "document.json"

    @property
    def source_pdf(self) -> Path:
        """The PDF as imported."""
        return self.directory / "source.pdf"

    @property
    def ocr_settings_file(self) -> Path:
        """What the OCR ran with, as JSON."""
        return self.directory / "ocr" / "settings.json"

    @property
    def ocr_markdown_file(self) -> Path:
        """The Markdown the model wrote, before it was read into the tree."""
        return self.directory / "ocr" / "draft.md"

    @property
    def ocr_result_file(self) -> Path:
        """The OcrResult the OCR read, as JSON."""
        return self.directory / "ocr" / "result.json"

    @property
    def ocr_pages_dir(self) -> Path:
        """Every page as the model saw it, figures boxed, as page_<N>.png."""
        return self.directory / "ocr" / "pages"

    @property
    def level_settings_file(self) -> Path:
        """What the Leveler ran with, as JSON."""
        return self.directory / "level" / "settings.json"

    @property
    def level_result_file(self) -> Path:
        """The OcrResult nested by heading level, as JSON."""
        return self.directory / "level" / "result.json"

    def log_file(self, stage: Stage) -> Path:
        """Where the logging of the last run of `stage` goes."""
        return self.directory / "logs" / f"{stage}.log"

    def has_result(self, stage: Stage) -> bool:
        """Whether `stage` has run to the end over the document."""
        return self._result_file(stage).is_file()

    def read_metadata(self) -> DocumentMetadata:
        """The metadata written as the document was imported."""
        return DocumentMetadata(**_read_json(self.metadata_file))

    def write_metadata(self, metadata: DocumentMetadata) -> None:
        """Writes the metadata, which names the folder a document."""
        _write_text_atomically(self.metadata_file, _dump_json(asdict(metadata)))

    def write_ocr_output(
        self,
        settings: Mapping[str, Any],
        markdown: str,
        result: OcrResult,
        rendered_pages: Sequence[Image],
    ) -> None:
        """Writes what an OCR run produced, dropping any earlier run and the
        Leveler's result, which was nested from the earlier tree.

        Args:
            settings: What the OCR ran with, as plain JSON values.
            markdown: The Markdown the model wrote.
            result: The OcrResult read from it.
            rendered_pages: Every page as the model saw it.
        """
        self._clear_stage("level")
        self._clear_stage("ocr")

        _write_text_atomically(self.ocr_settings_file, _dump_json(settings))
        _write_text_atomically(self.ocr_markdown_file, markdown)
        self.ocr_pages_dir.mkdir(parents=True, exist_ok=True)
        for page_index, page in enumerate(rendered_pages):
            page.save(self.ocr_pages_dir / f"page_{page_index}.png")
        _write_text_atomically(self.ocr_result_file, dump_ocr_result(result))

    def read_ocr_settings(self) -> dict[str, Any]:
        """What the last OCR run ran with."""
        return _read_json(self.ocr_settings_file)

    def read_ocr_result(self) -> OcrResult:
        """The OcrResult of the last OCR run."""
        return load_ocr_result(self.ocr_result_file.read_text(encoding="utf-8"))

    def write_level_output(
        self, settings: Mapping[str, Any], result: OcrResult
    ) -> None:
        """Writes what a Leveler run produced, dropping any earlier run.

        Args:
            settings: What the Leveler ran with, as plain JSON values.
            result: The nested OcrResult.
        """
        self._clear_stage("level")

        _write_text_atomically(self.level_settings_file, _dump_json(settings))
        _write_text_atomically(self.level_result_file, dump_ocr_result(result))

    def read_level_settings(self) -> dict[str, Any]:
        """What the last Leveler run ran with."""
        return _read_json(self.level_settings_file)

    def read_level_result(self) -> OcrResult:
        """The nested OcrResult of the last Leveler run."""
        return load_ocr_result(self.level_result_file.read_text(encoding="utf-8"))

    def _result_file(self, stage: Stage) -> Path:
        """The file whose presence says `stage` has run to the end."""
        return self.ocr_result_file if stage == "ocr" else self.level_result_file

    def _clear_stage(self, stage: Stage) -> None:
        """Removes a stage's output, result first, so a half-removed stage
        never looks done."""
        result_file = self._result_file(stage)
        result_file.unlink(missing_ok=True)
        shutil.rmtree(result_file.parent, ignore_errors=True)


def _dump_json(data: Mapping[str, Any]) -> str:
    """Indented JSON, its text left unescaped."""
    return json.dumps(data, ensure_ascii=False, indent=2)


def _read_json(path: Path) -> dict[str, Any]:
    """A JSON object read from `path`."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} does not hold a JSON object")
    return data


def _write_text_atomically(path: Path, text: str) -> None:
    """Writes `text` to `path` so that a reader sees the old file or the new
    one whole, never a part of it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)
