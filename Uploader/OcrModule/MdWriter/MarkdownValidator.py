"""Checking a page's Markdown against what the page was asked to hold."""

from collections import Counter
from collections.abc import Collection

from .Containers import fence_problems
from .Markers import (
    CONTINUED_BY_NEXT_MARKER,
    CONTINUED_BY_NEXT_PATTERN,
    CONTINUES_PREVIOUS_MARKER,
    CONTINUES_PREVIOUS_PATTERN,
    find_figure_references,
    split_continuation,
)
from .Schema import PageTask

# Shortest paragraph a repeat of is taken as the page transcribed twice, not a
# phrase the document itself repeats.
MIN_REPEATED_PARAGRAPH_LENGTH = 40

# How much of a repeated paragraph is quoted back to the model.
QUOTED_LENGTH = 40


def validate_page_output(
    markdown: str,
    task: PageTask,
    figure_ids: Collection[int],
    has_next: bool,
) -> list[str]:
    """What is wrong with a page's Markdown, as one line per problem for the model.

    An empty list means the output can be used as it is.

    Args:
        markdown: The Markdown the model returned for the page, page markers
            taken out.
        task: The page it was asked to write.
        figure_ids: The ids of the figures on the page.
        has_next: Whether a page follows, which a fill page may continue into.
    """
    problems = _continuation_problems(markdown, task, has_next)
    body = split_continuation(markdown).body

    problems += _figure_problems(body, figure_ids)
    problems += fence_problems(body)
    problems += _repetition_problems(body)

    return problems


def _continuation_problems(
    markdown: str,
    task: PageTask,
    has_next: bool,
) -> list[str]:
    """Continuation markers that are not allowed, or not where they belong."""
    split = split_continuation(markdown)
    leading_count = len(CONTINUES_PREVIOUS_PATTERN.findall(markdown))
    trailing_count = len(CONTINUED_BY_NEXT_PATTERN.findall(markdown))
    problems: list[str] = []

    if task.kind == "write":
        if leading_count or trailing_count:
            problems.append(
                f"Do not write {CONTINUES_PREVIOUS_MARKER} or "
                f"{CONTINUED_BY_NEXT_MARKER}: there is no neighbouring page to "
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
            f"Do not write {CONTINUED_BY_NEXT_MARKER}: no page follows yours, so "
            "nothing continues your last paragraph."
        )

    return problems


def _figure_problems(body: str, figure_ids: Collection[int]) -> list[str]:
    """Figures placed that are not on the page, placed twice, or not at all."""
    counts = Counter(find_figure_references(body))
    problems: list[str] = []

    unknown = sorted(set(counts) - set(figure_ids))
    if unknown:
        problems.append(
            f"There is no figure {_list(unknown)} on your page; "
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


def _repetition_problems(body: str) -> list[str]:
    """Long paragraphs written more than once, the sign of a page read twice."""
    paragraphs = [paragraph.strip() for paragraph in body.split("\n\n")]
    counts = Counter(
        paragraph
        for paragraph in paragraphs
        if len(paragraph) >= MIN_REPEATED_PARAGRAPH_LENGTH
    )

    return [
        f'This paragraph is written {count} times: "{paragraph[:QUOTED_LENGTH]}...". '
        "Transcribe the page once, from its image."
        for paragraph, count in counts.items()
        if count > 1
    ]


def _list(ids: list[int]) -> str:
    """The ids as one comma-separated list."""
    return ", ".join(str(figure_id) for figure_id in ids)
