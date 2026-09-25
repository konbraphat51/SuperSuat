"""The `:::name` blocks the model writes notes in: checking and joining their fences."""

import re

# The block containers the model writes notes in (see Docs/MarkdownSyntax.md).
NOTE_CONTAINERS = ("sidenote", "column")

# A line opening a note block, as `:::sidenote`.
OPEN_FENCE_PATTERN = re.compile(
    rf"^[ \t]*:::[ \t]*({'|'.join(NOTE_CONTAINERS)})[ \t]*$", re.MULTILINE
)

# A line closing the note block open, as `:::`.
CLOSE_FENCE_PATTERN = re.compile(r"^[ \t]*:::[ \t]*$", re.MULTILINE)

# Either kind of fence line, in the order they appear.
_FENCE_PATTERN = re.compile(
    rf"{OPEN_FENCE_PATTERN.pattern}|{CLOSE_FENCE_PATTERN.pattern}", re.MULTILINE
)


def fence_problems(text: str) -> list[str]:
    """What is wrong with the note blocks' fences, as one line per problem for the model."""
    problems: list[str] = []
    open_name: str | None = None

    for match in _FENCE_PATTERN.finditer(text):
        name = match.group(1)

        if name is not None and open_name is not None:
            problems.append(
                f":::{name} is opened inside the :::{open_name} block; close "
                "one block before opening the next, never nest them."
            )
        elif name is None and open_name is None:
            problems.append("A ::: line closes no block; remove it.")

        open_name = name

    if open_name is not None:
        problems.append(
            f"The last :::{open_name} block is never closed; end it with a ::: line, "
            "even if the box carries on past your page."
        )

    return problems


def closing_container(text: str) -> str | None:
    """The name of the note block the text ends by closing, or None."""
    stripped = text.rstrip()
    closes = [m for m in CLOSE_FENCE_PATTERN.finditer(stripped)]

    if not closes or closes[-1].end() != len(stripped):
        return None

    opens = list(OPEN_FENCE_PATTERN.finditer(stripped, 0, closes[-1].start()))
    return opens[-1].group(1) if opens else None


def opening_container(text: str) -> str | None:
    """The name of the note block the text starts by opening, or None."""
    match = OPEN_FENCE_PATTERN.match(text.lstrip("\n"))
    return match.group(1) if match else None


def drop_closing_fence(text: str) -> str:
    """The text without the fence line that ends it."""
    stripped = text.rstrip()
    closes = list(CLOSE_FENCE_PATTERN.finditer(stripped))
    return stripped[: closes[-1].start()].rstrip()


def drop_opening_fence(text: str) -> str:
    """The text without the fence line that starts it."""
    stripped = text.lstrip("\n")
    match = OPEN_FENCE_PATTERN.match(stripped)
    return stripped[match.end() :].lstrip() if match else text
