"""Tests for the stitched Markdown being read back into the document tree."""

from OcrModule.MdWriter.Parser.MarkdownParser import parse_markdown
from OcrModule.MdWriter.Schema import DetectedFigure
from OcrModule.OcrSchema import (
    OcrResultBlock,
    OcrResultBlockFigure,
    OcrResultBlockTableOfContents,
    OcrResultBlockText,
    OcrResultSection,
    TableOfContentsEntry,
)


def figure(block_id: int, page_index: int) -> DetectedFigure:
    return DetectedFigure(
        block_id=block_id, page_index=page_index, bounding_box=(1, 2, 3, 4)
    )


def flatten(section: OcrResultSection) -> list[OcrResultBlock]:
    """Every non-section block of the tree, in document order."""
    blocks: list[OcrResultBlock] = []
    for block in section.section_content:
        if isinstance(block, OcrResultSection):
            blocks += flatten(block)
        else:
            blocks.append(block)
    return blocks


def summary(section: OcrResultSection) -> list[tuple[str, str, list[int]]]:
    """(block_type, text or caption, existing_pages) of every block."""
    return [
        (
            block.block_type,
            (
                block.text
                if isinstance(block, OcrResultBlockText)
                else block.caption if isinstance(block, OcrResultBlockFigure) else ""
            ),
            block.existing_pages,
        )
        for block in flatten(section)
    ]


def test_every_kind_of_block_is_read_as_its_type():
    markdown = """<!--page:0-->
## Title

Body with a note[^1] and $x$.

- one
- two

```python
print(1)
```

$$
E = mc^2
$$

| a | b |
|---|---|
| 1 | 2 |

[^1]: the note

:::sidenote
in the margin
:::

:::column
a boxed column
:::
"""

    result = parse_markdown(markdown, [])

    assert summary(result.root_section) == [
        ("heading", "Title", [0]),
        ("paragraph", "Body with a note[^1] and $x$.", [0]),
        ("paragraph", "- one\n- two", [0]),
        ("code", "print(1)", [0]),
        ("math", "E = mc^2", [0]),
        ("table", "| a | b |\n|---|---|\n| 1 | 2 |", [0]),
        ("note", "[^1]: the note", [0]),
        ("note", "in the margin", [0]),
        ("note", "a boxed column", [0]),
    ]


def test_a_footnote_label_reused_by_a_later_part_is_still_a_note():
    markdown = "<!--page:0-->[^1]: first\n\n<!--page:1-->[^1]: word"

    result = parse_markdown(markdown, [])

    assert summary(result.root_section) == [
        ("note", "[^1]: first", [0]),
        ("note", "[^1]: word", [1]),
    ]


def test_each_heading_opens_a_section_under_the_root():
    markdown = "<!--page:0-->intro\n\n# A\n\ntext a\n\n### B\n\ntext b"

    root = parse_markdown(markdown, []).root_section

    assert isinstance(root.section_content[0], OcrResultBlockText)
    sections = root.section_content[1:]
    assert all(isinstance(s, OcrResultSection) for s in sections)
    assert [[b.block_type for b in s.section_content] for s in sections] == [  # type: ignore[attr-defined]
        ["heading", "paragraph"],
        ["heading", "paragraph"],
    ]


def test_a_paragraph_over_a_page_turn_is_on_both_pages():
    markdown = (
        "<!--page:0-->first\n\n"
        "runs over <!--page:1-->the page turn\n\n"
        "after\n<!--page:2-->\nand a marker line inside"
    )

    result = parse_markdown(markdown, [])

    assert summary(result.root_section) == [
        ("paragraph", "first", [0]),
        ("paragraph", "runs over the page turn", [0, 1]),
        ("paragraph", "after\nand a marker line inside", [1, 2]),
    ]
    assert result.root_section.existing_pages == [0, 1, 2]


def test_a_marker_ending_a_paragraph_belongs_to_the_next_one():
    result = parse_markdown("<!--page:0-->end<!--page:1-->\n\nnext", [])

    assert summary(result.root_section) == [
        ("paragraph", "end", [0]),
        ("paragraph", "next", [1]),
    ]


def test_a_placed_figure_takes_its_box_from_the_detection():
    markdown = "<!--page:0-->text\n\n<!--page:1-->![Figure 1: a cat](figure:5)"

    blocks = flatten(parse_markdown(markdown, [figure(5, 1)]).root_section)

    assert isinstance(blocks[1], OcrResultBlockFigure)
    assert blocks[1].caption == "Figure 1: a cat"
    assert blocks[1].bounding_box == (1, 2, 3, 4)
    assert blocks[1].existing_pages == [1]


def test_an_unknown_or_repeated_figure_is_dropped():
    markdown = "<!--page:0-->![a](figure:0)\n\n![b](figure:0)\n\n![c](figure:9)"

    blocks = flatten(parse_markdown(markdown, [figure(0, 0)]).root_section)

    assert [b.block_type for b in blocks] == ["figure"]


def test_an_unplaced_figure_goes_after_the_last_block_of_its_page():
    markdown = "<!--page:0-->a\n\n<!--page:1-->b\n\nc\n\n<!--page:3-->d"

    result = parse_markdown(markdown, [figure(0, 1), figure(1, 2)])

    assert summary(result.root_section) == [
        ("paragraph", "a", [0]),
        ("paragraph", "b", [1]),
        ("paragraph", "c", [1]),
        ("figure", "", [1]),
        ("figure", "", [2]),
        ("paragraph", "d", [3]),
    ]


def test_block_indices_are_unique_and_in_document_order():
    markdown = "<!--page:0-->## A\n\nx\n\n## B\n\ny"

    root = parse_markdown(markdown, []).root_section
    indices = [root.block_index]
    for section in root.section_content:
        indices.append(section.block_index)
        if isinstance(section, OcrResultSection):
            indices += [block.block_index for block in section.section_content]

    assert indices == list(range(len(indices)))


def test_a_figure_inside_a_box_is_placed_right_after_the_box():
    markdown = (
        "<!--page:0-->:::column\n![photo](figure:3)\n\nabout the author\n:::\n\nafter"
    )

    root = parse_markdown(markdown, [figure(3, 0)]).root_section

    assert summary(root) == [
        ("note", "about the author", [0]),
        ("figure", "photo", [0]),
        ("paragraph", "after", [0]),
    ]


def test_a_table_of_contents_is_read_as_its_nested_entries():
    markdown = (
        "<!--page:0-->## Contents\n\n"
        ":::toc\n- | Preface | iv\n- 1 | Introduction | 1\n  - 1.1 | Aims | 2\n:::\n\n"
        "after"
    )

    root = parse_markdown(markdown, []).root_section
    section = root.section_content[0]

    assert isinstance(section, OcrResultSection)
    toc = section.section_content[1]
    assert isinstance(toc, OcrResultBlockTableOfContents)
    assert toc.block_type == "table_of_contents"
    assert toc.existing_pages == [0]
    assert toc.entries == [
        TableOfContentsEntry(None, "Preface", "iv"),
        TableOfContentsEntry(
            "1", "Introduction", "1", [TableOfContentsEntry("1.1", "Aims", "2")]
        ),
    ]
    assert [b.block_type for b in section.section_content] == [
        "heading",
        "table_of_contents",
        "paragraph",
    ]


def test_a_table_of_contents_over_a_page_turn_is_one_block_nested_across_it():
    markdown = (
        "<!--page:0-->:::toc\n- 1 | Introduction | 1\n  - 1.1 | Aims | 2\n:::\n\n"
        "<!--page:1-->:::toc\n  - 1.2 | Scope | 5\n- 2 | Method | 9\n:::"
    )

    blocks = flatten(parse_markdown(markdown, []).root_section)

    assert len(blocks) == 1
    toc = blocks[0]
    assert isinstance(toc, OcrResultBlockTableOfContents)
    assert toc.existing_pages == [0, 1]
    assert [e.title for e in toc.entries] == ["Introduction", "Method"]
    assert [e.title for e in toc.entries[0].children] == ["Aims", "Scope"]


def test_tables_of_contents_apart_are_kept_apart():
    markdown = ":::toc\n- 1 | A | 1\n:::\n\nbetween\n\n:::toc\n- 2 | B | 2\n:::"

    blocks = flatten(parse_markdown(markdown, []).root_section)

    assert [b.block_type for b in blocks] == [
        "table_of_contents",
        "paragraph",
        "table_of_contents",
    ]
