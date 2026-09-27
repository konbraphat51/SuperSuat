"""Running one command line, from its arguments to its last event."""

import sys
import traceback
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from dotenv import load_dotenv

from Cli.Commands import COMMANDS
from Cli.Events import JsonLinesEvents
from Cli.Parser import build_parser
from DataStore.DataStore import DataStore

UPLOADER_ROOT = Path(__file__).resolve().parents[1]

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_INTERRUPTED = 130


def run(
    argv: Sequence[str],
    events_stream: TextIO,
    env_file: Path = UPLOADER_ROOT / ".env",
) -> int:
    """Runs the command `argv` names, writing its events to `events_stream`.

    A failure is told as an error event, with its traceback on stderr; wrong
    arguments are told by argparse on stderr, exiting with 2.

    Args:
        argv: The arguments, without the program name.
        events_stream: Where the JSON Lines go.
        env_file: The .env the API keys and the defaults are read from; a
            variable already set is kept.

    Returns:
        The exit code: 0 on success, 1 on failure, 130 when interrupted.
    """
    # .env is read before the arguments, whose defaults come from it
    load_dotenv(env_file)
    args = build_parser().parse_args(argv)
    events = JsonLinesEvents(events_stream)

    try:
        data = COMMANDS[args.command](args, DataStore(args.data_dir), events)
    except KeyboardInterrupt as interrupt:
        events.error(interrupt)
        return EXIT_INTERRUPTED
    except Exception as error:
        traceback.print_exc(file=sys.stderr)
        events.error(error)
        return EXIT_FAILED

    events.result(data)
    return EXIT_OK
