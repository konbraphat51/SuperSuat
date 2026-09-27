"""The Uploader's command line: imports PDFs into Uploader/Data and runs the OCR
and the Leveler over them, for the GUI or a person to call.

stdout carries only JSON Lines events (see Cli/Events.py); everything else
that would be written there goes to stderr. See Docs/Cli.md.

Usage (from the `Uploader` directory):

    uv run python main.py import path/to/book.pdf
    uv run python main.py ocr <document_id> --max-pages 5
    uv run python main.py level <document_id>
"""

import os
import sys
from typing import TextIO

# tqdm reads its settings as it is imported; the progress goes out as events instead
os.environ.setdefault("TQDM_DISABLE", "1")


def claim_stdout() -> TextIO:
    """The process's stdout, for the events alone: whatever else writes to it,
    from Python or from native code, goes to stderr from now on."""
    sys.stdout.flush()
    events_stream = os.fdopen(os.dup(1), "w", encoding="utf-8", newline="\n")
    os.dup2(2, 1)
    sys.stdout = sys.stderr
    return events_stream


def main() -> int:
    """Runs the command the arguments name, returning its exit code."""
    events_stream = claim_stdout()

    from Cli.App import run

    return run(sys.argv[1:], events_stream)


if __name__ == "__main__":
    raise SystemExit(main())
