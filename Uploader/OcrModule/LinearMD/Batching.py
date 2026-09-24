"""Splitting a document's pages into the batches the two passes transcribe."""

from .Schema import PageBatch

# Fewest pages a batch spans: with fewer, an odd batch has no inner page to fill.
MIN_BATCH_SIZE = 2


def plan_batches(page_count: int, batch_size: int) -> list[PageBatch]:
    """The batches covering every page, in document order.

    Batch `x` spans the closed range `[batch_size*x, batch_size*(x+1)]`, cut
    short at the last page, so neighbouring batches share their boundary page.
    Even batches write all of their pages; odd batches write only the pages
    no even batch has, and an odd batch left with none is not planned.

    Args:
        page_count: How many pages the document has.
        batch_size: How many pages apart the batches start; at least MIN_BATCH_SIZE.

    Raises:
        ValueError: batch_size is below MIN_BATCH_SIZE.
    """
    if batch_size < MIN_BATCH_SIZE:
        raise ValueError(
            f"batch_size must be at least {MIN_BATCH_SIZE}, got {batch_size}"
        )

    last_page = page_count - 1
    ranges = [
        (index, index * batch_size, min((index + 1) * batch_size, last_page))
        for index in range(page_count)
        if index * batch_size <= last_page
    ]

    written_by_even = {
        page
        for index, first, last in ranges
        if index % 2 == 0
        for page in range(first, last + 1)
    }

    batches: list[PageBatch] = []

    for index, first, last in ranges:
        pages = range(first, last + 1)
        written = (
            tuple(pages)
            if index % 2 == 0
            else tuple(page for page in pages if page not in written_by_even)
        )

        if written:
            batches.append(
                PageBatch(
                    index=index, first_page=first, last_page=last, written_pages=written
                )
            )

    return batches
