"""What each command does, given its arguments and the store."""

import argparse
import logging
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from Cli.DocumentView import describe_document
from Cli.Events import JsonLinesEvents
from Cli.Parser import level_settings_of, ocr_settings_of
from DataStore.DataStore import DataStore
from Pipeline.Builders import build_leveler, build_md_writer_ocr
from Pipeline.ChatModels import Provider
from Pipeline.LevelPipeline import LevelPipeline
from Pipeline.OcrPipeline import OcrPipeline

Command = Callable[[argparse.Namespace, DataStore, JsonLinesEvents], Any]
"""Runs one command, returning what its result event carries."""

# Libraries whose INFO logging is noise in a pipeline's log.
_NOISY_LOGGERS = ("boto3", "botocore", "urllib3", "httpx", "openai")


class MissingApiKeyError(RuntimeError):
    """The provider a pipeline runs on has no API key to call it with."""


def list_documents(
    args: argparse.Namespace, store: DataStore, events: JsonLinesEvents
) -> list[dict[str, Any]]:
    """Every stored document, the earliest imported first."""
    return [describe_document(document) for document in store.list_documents()]


def import_document(
    args: argparse.Namespace, store: DataStore, events: JsonLinesEvents
) -> dict[str, Any]:
    """The document the PDF was stored as."""
    return describe_document(store.import_pdf(args.pdf, args.name))


def show_document(
    args: argparse.Namespace, store: DataStore, events: JsonLinesEvents
) -> dict[str, Any]:
    """The document asked for."""
    return describe_document(store.open(args.document_id))


def delete_document(
    args: argparse.Namespace, store: DataStore, events: JsonLinesEvents
) -> dict[str, Any]:
    """The id of the document removed."""
    store.delete(args.document_id)
    return {"document_id": args.document_id}


def ocr_document(
    args: argparse.Namespace, store: DataStore, events: JsonLinesEvents
) -> dict[str, Any]:
    """The document, read by the OCR."""
    document = store.open(args.document_id)
    settings = ocr_settings_of(args)
    _require_api_key(settings.provider)

    with _logging_to(document.log_file("ocr"), args.log_level):
        OcrPipeline(settings, build_md_writer_ocr, events).run(document)
    return describe_document(document)


def level_document(
    args: argparse.Namespace, store: DataStore, events: JsonLinesEvents
) -> dict[str, Any]:
    """The document, its OcrResult leveled."""
    document = store.open(args.document_id)
    settings = level_settings_of(args)
    _require_api_key(settings.provider)

    with _logging_to(document.log_file("level"), args.log_level):
        LevelPipeline(settings, build_leveler, events).run(document)
    return describe_document(document)


COMMANDS: dict[str, Command] = {
    "list": list_documents,
    "import": import_document,
    "show": show_document,
    "delete": delete_document,
    "ocr": ocr_document,
    "level": level_document,
}
"""Every command, by the name it is called by."""


def _require_api_key(provider: Provider) -> None:
    """Fails before anything is loaded when the OpenAI key is missing; Bedrock
    may be reached without one, through the AWS credentials."""
    if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        raise MissingApiKeyError("OPENAI_API_KEY is not set")


@contextmanager
def _logging_to(log_file: Path, level: str) -> Iterator[None]:
    """Sends every log record at `level` or above to `log_file` while the block runs."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S"
        )
    )
    root = logging.getLogger()
    previous_level = root.level
    root.addHandler(handler)
    root.setLevel(level)
    for noisy in _NOISY_LOGGERS:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    try:
        yield
    finally:
        root.removeHandler(handler)
        root.setLevel(previous_level)
        handler.close()
