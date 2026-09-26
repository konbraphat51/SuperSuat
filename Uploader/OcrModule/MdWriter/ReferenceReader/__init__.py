"""Readers of a page's plain text, handed to the model as a reference.

Only the names asked for are imported: each implementation pulls in a heavy
framework of its own.
"""

from typing import TYPE_CHECKING, Any

from .ReferenceReader import ReferenceReader

if TYPE_CHECKING:
    from .Yomitoku import YomitokuReferenceReader

# The module each implementation lives in, imported on first use.
_LAZY_MODULES = {
    "YomitokuReferenceReader": ".Yomitoku",
}

__all__ = ["ReferenceReader", *_LAZY_MODULES]


def __getattr__(name: str) -> Any:
    """Imports an implementation's framework the first time it is asked for."""
    if name not in _LAZY_MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from importlib import import_module

    return getattr(import_module(_LAZY_MODULES[name], __name__), name)
