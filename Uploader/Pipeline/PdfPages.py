"""The pages of a PDF as images, each rendered only when it is read."""

from collections.abc import Sequence
from pathlib import Path
from types import TracebackType
from typing import Self, overload

import fitz  # PyMuPDF
from PIL import Image
from PIL.Image import Image as PilImage


class LazyPdfPages(Sequence[PilImage]):
    """The pages of a PDF as RGB images, so that a long document does not hold
    every page image at once. Closes the PDF when used as a context manager."""

    def __init__(self, pdf_path: Path, dpi: int, max_pages: int | None = None) -> None:
        """
        Args:
            pdf_path: The PDF to render.
            dpi: The resolution every page is rendered at.
            max_pages: Most pages to hold, counted from the first; None for all.
        """
        self._document = fitz.open(pdf_path)
        self._dpi = dpi
        page_count = len(self._document)
        self._page_count = (
            page_count if max_pages is None else min(page_count, max_pages)
        )

    def __len__(self) -> int:
        return self._page_count

    @overload
    def __getitem__(self, index: int) -> PilImage: ...

    @overload
    def __getitem__(self, index: slice) -> list[PilImage]: ...

    def __getitem__(self, index: int | slice) -> PilImage | list[PilImage]:
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(len(self)))]
        if not -len(self) <= index < len(self):
            raise IndexError(f"page {index} of {len(self)}")

        pixmap = self._document[index % len(self)].get_pixmap(dpi=self._dpi)
        return Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)

    def close(self) -> None:
        """Closes the PDF; no page can be read after."""
        self._document.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
