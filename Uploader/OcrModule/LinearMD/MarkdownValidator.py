"""Checking a batch's Markdown against what the batch was asked to write."""

from collections import Counter
from collections.abc import Collection

from .Containers import fence_problems
from .Markers import (
    CONTINUED_BY_NEXT_MARKER,
    CONTINUED_BY_NEXT_PATTERN,
    CONTINUES_PREVIOUS_MARKER,
    CONTINUES_PREVIOUS_PATTERN,
    find_figure_references,
    find_page_markers,
    page_marker,
    split_continuation,
    without_page_markers,
)
from .Schema import PageBatch


def validate_batch_output(
    markdown: str,
    batch: PageBatch,
    figure_ids: Collection[int],
    has_next: bool,
) -> list[str]:
    """What is wrong with a batch's Markdown, as one line per problem for the model.

    An empty list means the output can be used as it is.

    Args:
        markdown: The Markdown the model returned for the batch.
        batch: The batch it was asked to write.
        figure_ids: The ids of the figures on the pages the batch writes.
        has_next: Whether a batch follows, which a fill batch may continue into.
    """
    problems = _continuation_problems(markdown, batch, has_next)
    body = split_continuation(markdown).body

    problems += _page_marker_problems(body, batch)
    problems += _figure_problems(body, figure_ids)
    problems += fence_problems(without_page_markers(body))

    return problems


def _continuation_problems(
    markdown: str,
    batch: PageBatch,
    has_next: bool,
) -> list[str]:
    """Continuation markers that are not allowed, or not where they belong."""
    split = split_continuation(markdown)
    leading_count = len(CONTINUES_PREVIOUS_PATTERN.findall(markdown))
    trailing_count = len(CONTINUED_BY_NEXT_PATTERN.findall(markdown))
    problems: list[str] = []

    if batch.kind == "write":
        if leading_count or trailing_count:
            problems.append(
                f"Do not write {CONTINUES_PREVIOUS_MARKER} or "
                f"{CONTINUED_BY_NEXT_MARKER}: there is no neighbouring part to "
                "continue from or into."
            )
        return problems

    if leading_count > int(split.continues_previous):
        problems.append(
            f"{CONTINUES_PREVIOUS_MARKER} may only appear once, as the very first "
            "thing of your output."
        )

    if trailing_count > int(split.continued_by_next):
        problems.append(
            f"{CONTINUED_BY_NEXT_MARKER} may only appear once, as the very last "
            "thing of your output."
        )

    if split.continued_by_next and not has_next:
        problems.append(
            f"Do not write {CONTINUED_BY_NEXT_MARKER}: no part follows yours, so "
            "nothing continues your last paragraph."
        )

    return problems


def _page_marker_problems(body: str, batch: PageBatch) -> list[str]:
    """Page markers missing, repeated, out of order, or not opening the output."""
    written = list(batch.written_pages)
    found = find_page_markers(body)
    problems: list[str] = []

    if found != written:
        expected = ", ".join(page_marker(page) for page in written)
        actual = ", ".join(page_marker(page) for page in found) or "none"
        problems.append(
            f"Write exactly these page markers, once each and in this order: "
            f"{expected}. Your output has: {actual}."
        )

    if not body.startswith(page_marker(written[0])):
        problems.append(
            f"Start your output with {page_marker(written[0])}"
            + (
                f" (after {CONTINUES_PREVIOUS_MARKER}, if you use it)"
                if batch.kind == "fill"
                else ""
            )
            + "."
        )

    return problems


def _figure_problems(body: str, figure_ids: Collection[int]) -> list[str]:
    """Figures placed that are not on these pages, placed twice, or not at all."""
    counts = Counter(find_figure_references(body))
    problems: list[str] = []

    unknown = sorted(set(counts) - set(figure_ids))
    if unknown:
        problems.append(
            f"There is no figure {_list(unknown)} on the pages you are writing; "
            "remove those references."
        )

    repeated = sorted(
        fid for fid, count in counts.items() if count > 1 and fid in figure_ids
    )
    if repeated:
        problems.append(f"Place figure {_list(repeated)} only once each.")

    missing = sorted(set(figure_ids) - set(counts))
    if missing:
        problems.append(
            f"Figure {_list(missing)} is not placed; write each one as "
            "![caption](figure:ID) where it stands in the reading order."
        )

    return problems


def _list(ids: list[int]) -> str:
    """The ids as one comma-separated list."""
    return ", ".join(str(figure_id) for figure_id in ids)
