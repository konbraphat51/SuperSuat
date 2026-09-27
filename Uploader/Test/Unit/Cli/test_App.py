"""Tests for running a command line, from its arguments to its events."""

import io
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import pytest
from PIL.Image import Image

from Cli import Commands
from Cli.App import EXIT_FAILED, EXIT_OK, run
from OcrModule.Blocked.PageParallel import run_parallel
from OcrModule.MdWriter.Schema import MarkdownDraft
from OcrModule.OcrSchema import OcrResult
from Pipeline.Settings import LevelSettings, OcrSettings


class FakeWriter:
    """Writes every page as a heading, reporting its progress as MdWriterOcr does."""

    def write_markdown(self, all_page_images: list[Image]) -> MarkdownDraft:
        pages = run_parallel(
            lambda index: f"# Page {index}",
            list(range(len(all_page_images))),
            progress_label="writing",
        )
        return MarkdownDraft("\n\n".join(pages), [], list(all_page_images))


class FakeLeveler:
    """Leaves every tree as it is."""

    def level_ocr_result(
        self, all_page_images: Sequence[Image], ocr_result: OcrResult
    ) -> OcrResult:
        return ocr_result


class Cli:
    """Runs command lines against a store of its own, keeping their events."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.built_ocr: list[OcrSettings] = []
        self.built_levelers: list[LevelSettings] = []

    def __call__(self, *argv: str) -> tuple[int, list[dict[str, Any]]]:
        """The exit code and the events of one command line."""
        stream = io.StringIO()
        code = run(
            ["--data-dir", str(self.data_dir), *argv],
            stream,
            env_file=self.data_dir / "missing.env",
        )
        return code, [json.loads(line) for line in stream.getvalue().splitlines()]

    def result(self, *argv: str) -> Any:
        """What a command line that succeeds carries in its result event."""
        code, events = self(*argv)
        assert code == EXIT_OK, events
        assert events[-1]["event"] == "result"
        return events[-1]["data"]

    def build_ocr(self, settings: OcrSettings) -> FakeWriter:
        self.built_ocr.append(settings)
        return FakeWriter()

    def build_leveler(self, settings: LevelSettings) -> FakeLeveler:
        self.built_levelers.append(settings)
        return FakeLeveler()


@pytest.fixture
def cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Cli:
    """A command line on an empty store, its pipelines faked, with an OpenAI key set."""
    cli = Cli(tmp_path / "Data")
    monkeypatch.setattr(Commands, "build_md_writer_ocr", cli.build_ocr)
    monkeypatch.setattr(Commands, "build_leveler", cli.build_leveler)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    for name in ("OCR_PROVIDER", "OCR_MODEL_ID", "LEVELER_MODEL_ID"):
        monkeypatch.delenv(name, raising=False)
    return cli


@pytest.fixture
def pdf_path(tmp_path: Path) -> Path:
    """A PDF of two blank pages."""
    path = tmp_path / "book.pdf"
    with fitz.open() as pdf:
        pdf.new_page(width=72, height=72)
        pdf.new_page(width=72, height=72)
        pdf.save(path)
    return path


def test_an_empty_store_lists_nothing(cli: Cli):
    assert cli.result("list") == []


def test_an_imported_document_is_described_and_listed(cli: Cli, pdf_path: Path):
    imported = cli.result("import", str(pdf_path), "--name", "Book")

    assert imported["name"] == "Book"
    assert imported["page_count"] == 2
    assert Path(imported["source_pdf"]).is_file()
    assert imported["stages"]["ocr"]["done"] is False
    assert imported["stages"]["level"]["done"] is False
    assert cli.result("list") == [imported]
    assert cli.result("show", imported["document_id"]) == imported


def test_a_deleted_document_is_no_longer_listed(cli: Cli, pdf_path: Path):
    document_id = cli.result("import", str(pdf_path))["document_id"]

    assert cli.result("delete", document_id) == {"document_id": document_id}
    assert cli.result("list") == []


def test_a_failure_ends_on_an_error_event(cli: Cli):
    code, events = cli("show", "0" * 32)

    assert code == EXIT_FAILED
    assert events == [
        {
            "event": "error",
            "type": "DocumentNotFoundError",
            "message": f"No document {'0' * 32}",
        }
    ]


def test_ocr_tells_its_steps_and_progress_then_the_document(cli: Cli, pdf_path: Path):
    document_id = cli.result("import", str(pdf_path))["document_id"]

    code, events = cli("ocr", document_id, "--dpi", "100", "--max-pages", "1")

    assert code == EXIT_OK
    assert [e["name"] for e in events if e["event"] == "step"] == [
        "loading",
        "rendering",
        "transcribing",
        "parsing",
        "saving",
    ]
    assert {"event": "progress", "label": "writing", "done": 1, "total": 1} in events
    ocr = events[-1]["data"]["stages"]["ocr"]
    assert ocr["done"] is True
    assert ocr["settings"]["dpi"] == 100
    assert Path(ocr["result_file"]).is_file()
    assert Path(ocr["log_file"]).is_file()
    assert cli.built_ocr[0].max_pages == 1


def test_ocr_takes_the_provider_default_model(cli: Cli, pdf_path: Path):
    document_id = cli.result("import", str(pdf_path))["document_id"]

    cli.result("ocr", document_id, "--provider", "bedrock")

    assert cli.built_ocr[0].model == "qwen.qwen3-vl-235b-a22b"


def test_none_leaves_the_figure_corrector_out(cli: Cli, pdf_path: Path):
    document_id = cli.result("import", str(pdf_path))["document_id"]

    cli.result("ocr", document_id, "--figure-corrector-model", "none")

    assert cli.built_ocr[0].figure_corrector_model is None


def test_level_runs_over_the_ocr_result(cli: Cli, pdf_path: Path):
    document_id = cli.result("import", str(pdf_path))["document_id"]
    cli.result("ocr", document_id)

    document = cli.result("level", document_id, "--model", "some-model")

    assert document["stages"]["level"]["done"] is True
    assert document["stages"]["level"]["settings"]["model"] == "some-model"


def test_level_before_ocr_fails(cli: Cli, pdf_path: Path):
    document_id = cli.result("import", str(pdf_path))["document_id"]

    code, events = cli("level", document_id)

    assert code == EXIT_FAILED
    assert events[-1]["type"] == "MissingOcrResultError"


def test_openai_without_a_key_fails_before_anything_is_built(
    cli: Cli, pdf_path: Path, monkeypatch: pytest.MonkeyPatch
):
    document_id = cli.result("import", str(pdf_path))["document_id"]
    monkeypatch.delenv("OPENAI_API_KEY")

    code, events = cli("ocr", document_id)

    assert code == EXIT_FAILED
    assert events[-1]["type"] == "MissingApiKeyError"
    assert cli.built_ocr == []
