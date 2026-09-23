"""Running a pipeline stage over several pages at the same time."""

from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

# How many pages a stage works on at once, unless it says otherwise. Pages are
# independent, so this is only bounded by what the machine behind the stage
# can take: a few calls in flight keeps a remote model busy without flooding
# it, and keeps a local one from holding several pages of tensors at once.
DEFAULT_MAX_PARALLEL_PAGES = 4

Item = TypeVar("Item")
Result = TypeVar("Result")


def map_pages(
    work: Callable[[Item], Result],
    items: Sequence[Item],
    max_parallel_pages: int = DEFAULT_MAX_PARALLEL_PAGES,
) -> list[Result]:
    """Runs `work` over `items`, several at a time, in input order.

    The results come back in the order of `items`, whatever order the work
    finished in, so a stage using this stays deterministic. One page, or one
    worker, runs on this thread instead, which keeps a stack trace readable.

    Args:
        work: What to do with one item. Called from several threads at once,
            so whatever it touches has to stand that.
        items: One entry per page, in the order the results are wanted in.
        max_parallel_pages: Most pages to work on at once.
    """
    if max_parallel_pages <= 1 or len(items) <= 1:
        return [work(item) for item in items]

    with ThreadPoolExecutor(
        max_workers=min(max_parallel_pages, len(items))
    ) as executor:
        return list(executor.map(work, items))
