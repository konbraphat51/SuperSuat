"""Running a pipeline stage over several pages, or several blocks, at once."""

import threading
from collections.abc import Callable, Iterable, Iterator, Sequence
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from typing import TypeVar

from tqdm import tqdm

# How many pages a stage works on at once, unless it says otherwise. Pages are
# independent, so this is only bounded by what the machine behind the stage
# can take: a few calls in flight keeps a remote model busy without flooding
# it, and keeps a local one from holding several pages of tensors at once.
DEFAULT_MAX_PARALLEL_PAGES = 4

Item = TypeVar("Item")
Result = TypeVar("Result")

ProgressListener = Callable[[str, int, int], None]
"""Told of a labelled stage's progress: its label, the items done, and the items in all."""

_listeners: list[ProgressListener] = []
_listeners_lock = threading.Lock()


@contextmanager
def listening_progress(listener: ProgressListener) -> Iterator[None]:
    """Tells `listener` of every labelled stage run while the block runs.

    Listeners are process-wide, so a stage run from any thread is reported.
    It is told once as a stage starts, with nothing done, and once per item.
    """
    with _listeners_lock:
        _listeners.append(listener)
    try:
        yield
    finally:
        with _listeners_lock:
            _listeners.remove(listener)


def run_parallel(
    work: Callable[[Item], Result],
    items: Sequence[Item],
    max_parallel: int = DEFAULT_MAX_PARALLEL_PAGES,
    progress_label: str | None = None,
    progress_unit: str = "page",
) -> list[Result]:
    """Runs `work` over `items`, several at a time, in input order.

    The results come back in the order of `items`, whatever order the work
    finished in, so a stage using this stays deterministic. One item, or one
    worker, runs on this thread instead, which keeps a stack trace readable.

    The first failure ends the run: whatever has not started is cancelled and
    the error is raised here. A document read half-way is not a result worth
    keeping, and failing at once says which page went wrong while the rest of
    the document has not yet been paid for.

    Args:
        work: What to do with one item. Called from several threads at once,
            so whatever it touches has to stand that.
        items: One entry per unit of work, in the order the results are wanted.
        max_parallel: Most items to work on at once.
        progress_label: What to call this stage in the progress bar and to
            the progress listeners, or None to show no bar and tell no one.
        progress_unit: What one item is called in that bar.
    """
    if max_parallel <= 1 or len(items) <= 1:
        return [
            work(item)
            for item in _tracked(items, progress_label, len(items), progress_unit)
        ]

    with ThreadPoolExecutor(max_workers=min(max_parallel, len(items))) as executor:
        futures = [executor.submit(work, item) for item in items]

        tracked = _tracked(
            as_completed(futures), progress_label, len(futures), progress_unit
        )
        try:
            for future in tracked:
                # raises the first failure, before the rest is waited on
                future.result()
        except BaseException:
            _cancel(executor, futures)
            raise

    return [future.result() for future in futures]


def _tracked(
    items: Iterable[Item],
    progress_label: str | None,
    total: int,
    progress_unit: str,
) -> Iterable[Item]:
    """The items as they are, wrapped in a progress bar when one is wanted."""
    if progress_label is None:
        return items

    bar = tqdm(items, desc=progress_label, total=total, unit=progress_unit)
    return _reported(bar, progress_label, total)


def _reported(items: Iterable[Item], label: str, total: int) -> Iterator[Item]:
    """The items as they are, telling the listeners as each one is done with."""
    _notify(label, 0, total)
    # an item is done with once the caller asks for the next one
    for done, item in enumerate(items, start=1):
        yield item
        _notify(label, done, total)


def _notify(label: str, done: int, total: int) -> None:
    """Tells every listener of a stage's progress."""
    with _listeners_lock:
        listeners = list(_listeners)

    for listener in listeners:
        listener(label, done, total)


def _cancel(executor: ThreadPoolExecutor, futures: list[Future]) -> None:
    """Drops whatever has not started yet, so a failed run stops paying.

    What is already running is left to finish: a thread cannot be stopped from
    outside, and the pool is joined on the way out either way.
    """
    for future in futures:
        future.cancel()

    executor.shutdown(wait=False, cancel_futures=True)
