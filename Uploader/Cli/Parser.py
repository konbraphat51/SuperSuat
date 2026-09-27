"""The arguments of every command, their defaults read from the environment."""

import argparse
import os
from pathlib import Path

from DataStore.DataStore import DEFAULT_DATA_ROOT
from Pipeline.ChatModels import PROVIDERS, Provider
from Pipeline.Settings import DETECTORS, REFERENCES, LevelSettings, OcrSettings

NO_FIGURE_CORRECTOR = "none"
"""What --figure-corrector-model takes to leave the correct_figures tool out."""

DEFAULT_OCR_MODEL_IDS: dict[Provider, str] = {
    "openai": OcrSettings().model,
    "bedrock": "qwen.qwen3-vl-235b-a22b",
}
"""The OCR model of each provider, unless --model or OCR_MODEL_ID names one."""

_OCR = OcrSettings()
_LEVEL = LevelSettings()


def build_parser() -> argparse.ArgumentParser:
    """The parser of every command. Build it after .env is loaded, which the
    defaults are read from."""
    parser = argparse.ArgumentParser(
        prog="main.py",
        description=(
            "Imports PDFs into Uploader/Data and runs the OCR and the Leveler "
            "over them. Writes JSON Lines to stdout: step and progress events "
            "as it goes, then one result or error event."
        ),
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_ROOT,
        help="Folder the documents are kept in. Default: Uploader/Data.",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Verbosity of the log a pipeline writes into its document's logs folder.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("list", help="List every stored document.")

    import_parser = commands.add_parser("import", help="Store a PDF as a new document.")
    import_parser.add_argument("pdf", type=Path)
    import_parser.add_argument(
        "--name", default=None, help="Default: the PDF's file name."
    )

    for name, help_text in (
        ("show", "Describe one document."),
        ("delete", "Remove a document and all its files."),
    ):
        commands.add_parser(name, help=help_text).add_argument("document_id")

    _add_ocr_parser(commands)
    _add_level_parser(commands)
    return parser


def ocr_settings_of(args: argparse.Namespace) -> OcrSettings:
    """The OcrSettings the arguments of the ocr command describe."""
    return OcrSettings(
        provider=args.provider,
        model=args.model or DEFAULT_OCR_MODEL_IDS[args.provider],
        reasoning_effort=args.reasoning_effort,
        max_tokens=args.max_tokens,
        detector=args.detector,
        reference=args.reference,
        figure_corrector_model=(
            None
            if args.figure_corrector_model == NO_FIGURE_CORRECTOR
            else args.figure_corrector_model
        ),
        max_figure_corrections=args.max_figure_corrections,
        dpi=args.dpi,
        max_parallel=args.max_parallel,
        max_pages=args.max_pages,
    )


def level_settings_of(args: argparse.Namespace) -> LevelSettings:
    """The LevelSettings the arguments of the level command describe."""
    return LevelSettings(
        provider=args.provider,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        max_tokens=args.max_tokens,
    )


def _add_ocr_parser(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """The ocr command: reads a document with MdWriter."""
    parser = commands.add_parser(
        "ocr",
        help="Read a document into its OcrResult, replacing any earlier one and its leveled tree.",
    )
    parser.add_argument("document_id")
    parser.add_argument(
        "--provider",
        choices=PROVIDERS,
        default=os.getenv("OCR_PROVIDER", _OCR.provider),
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OCR_MODEL_ID"),
        help="Default: OCR_MODEL_ID, else the provider's own default.",
    )
    parser.add_argument(
        "--reasoning-effort", default=os.getenv("OPENAI_REASONING_EFFORT")
    )
    parser.add_argument("--max-tokens", type=int, default=_OCR.max_tokens)
    parser.add_argument("--detector", choices=DETECTORS, default=_OCR.detector)
    parser.add_argument(
        "--reference",
        choices=REFERENCES,
        default=_OCR.reference,
        help="Local OCR whose text the model checks its characters against.",
    )
    parser.add_argument(
        "--figure-corrector-model",
        default=os.getenv("FIGURE_CORRECTOR_MODEL_ID", _OCR.figure_corrector_model),
        help=f'Bedrock model redrawing wrong figure boxes; "{NO_FIGURE_CORRECTOR}" leaves it out.',
    )
    parser.add_argument(
        "--max-figure-corrections", type=int, default=_OCR.max_figure_corrections
    )
    parser.add_argument("--dpi", type=int, default=_OCR.dpi)
    parser.add_argument(
        "--max-parallel",
        type=int,
        default=_OCR.max_parallel,
        help="Most pages sent to the model at once.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=_OCR.max_pages,
        help="Read only the first pages. Default: all.",
    )


def _add_level_parser(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]",
) -> None:
    """The level command: nests a document's OcrResult by heading level."""
    parser = commands.add_parser(
        "level",
        help="Nest a document's OcrResult by the level of every heading.",
    )
    parser.add_argument("document_id")
    parser.add_argument(
        "--provider",
        choices=PROVIDERS,
        default=os.getenv("LEVELER_PROVIDER", _LEVEL.provider),
    )
    parser.add_argument("--model", default=os.getenv("LEVELER_MODEL_ID", _LEVEL.model))
    parser.add_argument(
        "--reasoning-effort", default=os.getenv("LEVELER_REASONING_EFFORT")
    )
    parser.add_argument("--max-tokens", type=int, default=_LEVEL.max_tokens)
