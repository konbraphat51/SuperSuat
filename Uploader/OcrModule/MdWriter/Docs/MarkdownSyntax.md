# Markdown syntax

The Markdown the model writes in the MdWriter pipeline, and how
[MarkdownParser](../MarkdownParser.py) reads it back into an `OcrResult`. The
prompts ([prompt.py](../Transcriber/prompt.py)) and the parser follow this one
specification; change them together.

日本語版: [MarkdownSyntax.ja.md](MarkdownSyntax.ja.md)

## What the model writes

| Element | Syntax | Notes |
| --- | --- | --- |
| Page start | `<!--page:N-->` | Where the content of page N begins; N is 0-indexed, the number sent before the page image. One per transcribed page, in order. When a paragraph runs over a page turn, the marker goes inside it, on the same line |
| Paragraph | one line of text | Lines the page broke are joined as the script wants. Paragraphs are separated by a blank line |
| Heading | `## heading` | Every heading, the document's title included, is level 2 (batches are written independently, so their hierarchies cannot be matched up) |
| Figure | `![caption](figure:ID)` | A paragraph of its own. ID is the number drawn on the figure's red box. The caption goes in the alt text only, never again as body text |
| Math | `$...$`, `$$...$$` | KaTeX-compatible LaTeX. A display equation goes on lines of its own |
| Table | GFM pipe table | A merged cell is repeated in every cell it spans |
| Code | fenced code block | Source code and pseudocode |
| Footnote | `[^n]` in the body, `[^n]: text` as a paragraph | n is the printed mark. Two parts may reuse a label |
| Sidenote | `:::sidenote` … `:::` | Text in the margin, placed after the paragraph it sits beside |
| Column | `:::column` … `:::` | A box, sidebar or column set apart from the main text |

Not written: page numbers, running heads and running footers, and the red boxes
and id labels drawn on the pages.

A figure, footnote, sidenote or column never goes inside a paragraph: when one is
printed in the middle of a paragraph (a page turn included), the whole paragraph
comes first and the block after it.

Every answer is complete Markdown on its own: a `:::` block is closed before the
answer ends, even when the box carries on past its last page, and reopened at the
start of an answer whose first page begins inside the box. Blocks never nest.

### Continuation markers (fill batches only)

| Marker | Where | Meaning |
| --- | --- | --- |
| `<!--continues-previous-->` | The very start of the answer | Its first paragraph is the rest of the previous part's last paragraph |
| `<!--continued-by-next-->` | The very end of the answer | Its last paragraph carries on into the next part's first paragraph |

Where such a paragraph is inside a box, both answers hold it in a `:::` block of the
same name; the [Stitcher](../Stitcher.py) drops the closing and reopening fences at
the join, so the box becomes one block again.

## How it is checked

[MarkdownValidator](../MarkdownValidator.py) checks each answer before it is used. A
problem is sent back to the model, which writes the whole answer again, up to
`MAX_ATTEMPT_COUNT` (3) times:

- The page markers are exactly the pages the batch writes, once each, in order, and
  the answer starts with the first of them (after `<!--continues-previous-->`)
- Every figure on those pages is placed exactly once, and no other figure is
- The continuation markers are only in a fill batch, only at the start and the end,
  and `<!--continued-by-next-->` only when a part follows
- The `:::` fences are balanced and not nested
- No paragraph of 40 characters or more is written twice, which is what a page
  transcribed under the wrong marker looks like

## How it is read

The page markers are taken out before parsing, their offsets kept: an HTML comment
would otherwise cut a paragraph in two. A marker on a line of its own takes the line
with it, so a paragraph is not split either.

| Markdown (top level) | `OcrResult` |
| --- | --- |
| paragraph, list, blockquote, HTML | `paragraph` (a paragraph opening with `[^n]:` is a `note`; an HTML block of comments only is dropped) |
| heading | a new `OcrResultSection` under the root, holding a `heading` block and what follows up to the next heading |
| fenced or indented code | `code` (the code, without its fences) |
| `$$` block | `math` (without the `$$`) |
| table | `table` |
| `:::sidenote`, `:::column` | `note` (the inner text) |
| a paragraph of one `figure:ID` image | `OcrResultBlockFigure`: box and page from the detection, caption from the alt text |

A block's text is its Markdown source, as written. Link reference definitions are
turned off, since `[^1]: note` would otherwise be read as one and disappear.

`existing_pages` of a block is the page it starts on, plus every page whose marker
falls inside it before its last text. A section's is then the union of its contents'.

A figure placed with an id that was never detected, or placed a second time, is
dropped with a warning. A detected figure that is never placed goes after the last
block of its page, also with a warning.
