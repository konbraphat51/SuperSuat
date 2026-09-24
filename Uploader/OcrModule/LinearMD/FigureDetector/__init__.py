"""Figure detectors for the first stage of the LinearMD pipeline.

Only the names asked for are imported: each implementation pulls in a heavy
framework of its own, and a pipeline uses one of them.
"""

from typing import Any

from .FigureDetector import FigureDetector

# The module each implementation lives in, imported on first use.
_LAZY_MODULES: dict[str, str] = {}

__all__ = ["FigureDetector", *_LAZY_MODULES]


def __getattr__(name: str) -> Any:
    """Imports an implementation's framework the first time it is asked for."""
    if name not in _LAZY_MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from importlib import import_module

    return getattr(import_module(_LAZY_MODULES[name], __name__), name)
