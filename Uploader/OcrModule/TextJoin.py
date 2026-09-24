"""Joining two halves of one text that a page break split apart."""


def join_texts(former: str, latter: str) -> str:
    """Two halves of one block's text, joined as the script they are in wants.

    The line break the page forced was never part of the text, so it is not
    kept. A space takes its place only where both sides of the join are ASCII,
    which is what a script that separates words with spaces looks like;
    Japanese and Chinese are joined directly. A word the page split across a
    hyphen is joined directly too, hyphen kept, since dropping a hyphen that
    was the author's own cannot be undone.
    """
    former, latter = former.rstrip(), latter.lstrip()

    return f"{former}{join_separator(former, latter)}{latter}"


def join_separator(former: str, latter: str) -> str:
    """What goes between the two halves of a split text: a space, or nothing.

    Whitespace already at the join is not looked at; the characters either side
    of it decide, as `join_texts` describes.
    """
    former, latter = former.rstrip(), latter.lstrip()

    if not former or not latter:
        return ""

    needs_space = (
        former[-1].isascii() and latter[0].isascii() and not former.endswith("-")
    )

    return " " if needs_space else ""
