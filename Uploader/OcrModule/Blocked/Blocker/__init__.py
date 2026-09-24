"""Blocker implementations for the layout stage of the OCR pipeline.

Only the names asked for are imported: each implementation pulls in a heavy
framework of its own, and a pipeline uses one of them.
"""

from typing import TYPE_CHECKING

from .Blocker import Blocker
from .BlockRenderer import BlockRenderer

if TYPE_CHECKING:
    from .DocLayoutYolo import DocLayoutYoloBlocker
    from .PpStructure import PpStructureBlocker
    from .Yomitoku import YomitokuBlocker

# The module each implementation lives in, imported on first use.
_LAZY_MODULES = {
    "DocLayoutYoloBlocker": ".DocLayoutYolo",
    "PpStructureBlocker": ".PpStructure",
    "YomitokuBlocker": ".Yomitoku",
}

__all__ = ["Blocker", "BlockRenderer", *_LAZY_MODULES]


def __getattr__(name: str):
    """Imports an implementation's framework the first time it is asked for."""
    if name not in _LAZY_MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from importlib import import_module

    return getattr(import_module(_LAZY_MODULES[name], __name__), name)
