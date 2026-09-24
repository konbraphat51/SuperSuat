"""Tests for the helper every stage runs its pages through."""

import threading
import time

import pytest

from OcrModule.Blocked.PageParallel import run_parallel


def test_results_come_back_in_input_order():
    results = run_parallel(lambda item: item * 2, list(range(6)), 3)

    assert results == [0, 2, 4, 6, 8, 10]


def test_items_are_worked_on_at_the_same_time():
    threads: set[int] = set()
    lock = threading.Lock()

    def work(item: int) -> int:
        with lock:
            threads.add(threading.get_ident())
        time.sleep(0.05)
        return item

    run_parallel(work, list(range(4)), 4)

    assert len(threads) > 1


def test_the_first_failure_ends_the_run_without_working_through_the_rest():
    done: list[int] = []
    lock = threading.Lock()

    def work(item: int) -> int:
        if item == 0:
            raise ValueError("this page broke")
        time.sleep(0.05)
        with lock:
            done.append(item)
        return item

    with pytest.raises(ValueError, match="this page broke"):
        run_parallel(work, list(range(40)), 2)

    # whatever had not started is cancelled, so most of the work never ran
    assert len(done) < 40


def test_one_item_runs_on_the_calling_thread():
    calling_thread = threading.get_ident()

    (result,) = run_parallel(lambda item: threading.get_ident(), [0], 4)

    assert result == calling_thread
