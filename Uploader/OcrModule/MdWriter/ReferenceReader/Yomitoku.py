"""Reference text read with yomitoku's document analyzer."""

import logging
from typing import Any

from PIL.Image import Image
from yomitoku import DocumentAnalyzer

from ...Blocked.Blocker.Yomitoku import YomitokuBlocker
from .ReferenceReader import ReferenceReader

logger = logging.getLogger(__name__)

# The roles of the text the model is told to leave out.
SKIPPED_ROLES = ("page_header", "page_footer")

# What separates the cells of a table row in the reference.
CELL_SEPARATOR = " | "


class YomitokuReferenceReader(ReferenceReader):
    """Reads page text with yomitoku, which handles Japanese, vertical text included.

    Its paragraphs and tables are put in yomitoku's reading order; the text
    inside figures is left out, as the model is told to leave it."""

    def __init__(
        self,
        device: str | None = None,
        configs: dict[str, Any] | None = None,
    ) -> None:
        """Loads the analyzer's models onto `device`, or onto the best one available.

        Args:
            device: Torch device the models run on, e.g. "cuda" or "cpu".
            configs: Per-model yomitoku overrides, keyed by model name.
        """
        self._device = device or YomitokuBlocker.default_device()
        self._analyzer = DocumentAnalyzer(
            configs=configs or {},
            device=self._device,
            visualize=False,
        )
        logger.info("YomitokuReferenceReader ready on device=%s", self._device)

    def _read_page(self, page: Image) -> str:
        """The page's paragraphs and tables, in reading order."""
        result, _, _ = self._analyzer(YomitokuBlocker._to_bgr_array(page))

        blocks: list[tuple[int, str]] = [
            (paragraph.order, paragraph.contents)
            for paragraph in result.paragraphs
            if paragraph.role not in SKIPPED_ROLES
        ]
        blocks += [(table.order, _table_text(table)) for table in result.tables]

        return "\n\n".join(text for _, text in sorted(blocks) if text.strip())


def _table_text(table: Any) -> str:
    """A table's cells, row by row."""
    rows: dict[int, list[tuple[int, str]]] = {}
    for cell in table.cells:
        rows.setdefault(cell.row, []).append((cell.col, cell.contents))

    return "\n".join(
        CELL_SEPARATOR.join(text for _, text in sorted(cells))
        for _, cells in sorted(rows.items())
    )
