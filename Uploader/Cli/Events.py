"""Writing what a command does as JSON Lines, for the GUI to read as it goes."""

import json
import threading
from typing import Any, TextIO


class JsonLinesEvents:
    """Writes one JSON object per line, each naming its kind in "event":

    - {"event": "step", "name": ...}: a step of a pipeline has started
    - {"event": "progress", "label": ..., "done": ..., "total": ...}
    - {"event": "result", "data": ...}: the command succeeded; the last line
    - {"event": "error", "type": ..., "message": ...}: it failed; the last line

    Satisfies PipelineObserver. Every line is ASCII, whatever it carries, so
    no console code page can garble it, and is flushed as it is written.
    """

    def __init__(self, stream: TextIO) -> None:
        """
        Args:
            stream: Where the lines go; the process's stdout for the GUI.
        """
        self._stream = stream
        self._lock = threading.Lock()

    def step(self, name: str) -> None:
        """Tells that a step of a pipeline has started."""
        self._write({"event": "step", "name": name})

    def progress(self, label: str, done: int, total: int) -> None:
        """Tells that a labelled stage has done `done` of its `total` items."""
        self._write({"event": "progress", "label": label, "done": done, "total": total})

    def result(self, data: Any) -> None:
        """Tells what the command produced, as it succeeded."""
        self._write({"event": "result", "data": data})

    def error(self, error: BaseException) -> None:
        """Tells why the command failed."""
        self._write(
            {"event": "error", "type": type(error).__name__, "message": str(error)}
        )

    def _write(self, event: dict[str, Any]) -> None:
        """Writes one event as one line; stages on several threads may report at once."""
        line = json.dumps(event, ensure_ascii=True)
        with self._lock:
            self._stream.write(line + "\n")
            self._stream.flush()
