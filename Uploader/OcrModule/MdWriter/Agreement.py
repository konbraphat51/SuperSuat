"""How well a page's Markdown agrees with the reference text of the same page."""

import re
import unicodedata
from collections import Counter

# Any HTML comment, as the page and continuation markers.
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)

# A placed figure, whose alt text is the caption printed on the page.
_FIGURE = re.compile(r"!\[([^\]]*)\]\(\s*figure:\d+\s*\)")

# A LaTeX command; its letters are markup, not text on the page.
_LATEX_COMMAND = re.compile(r"\\[A-Za-z]+")


def agreement(markdown: str, reference: str) -> float:
    """The F1 score of the character bigrams the two texts share, from 0 to 1.

    Only letters and digits are compared, so Markdown syntax, punctuation and
    spacing do not count, nor does the order of paragraphs: text the model
    invented or repeated lowers it as much as text it left out. Two empty
    texts agree fully.

    Args:
        markdown: The page as the model wrote it.
        reference: The page as the reference reader read it.
    """
    written = _bigrams(_letters(markdown))
    read = _bigrams(_letters(reference))

    if not written and not read:
        return 1.0

    shared = sum((written & read).values())
    return 2 * shared / (sum(written.values()) + sum(read.values()))


def _letters(text: str) -> str:
    """The text reduced to its letters and digits."""
    text = _LATEX_COMMAND.sub("", _FIGURE.sub(r"\1", _COMMENT.sub("", text)))
    text = unicodedata.normalize("NFKC", text)
    return "".join(ch for ch in text if unicodedata.category(ch)[0] in "LN")


def _bigrams(text: str) -> Counter[str]:
    """How often each pair of neighbouring characters occurs."""
    return Counter(text[i : i + 2] for i in range(len(text) - 1))
