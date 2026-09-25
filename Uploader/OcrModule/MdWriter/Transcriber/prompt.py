"""The instructions the model transcribes a page into Markdown with."""

# The Markdown every page is written in, and MarkdownParser reads (see Docs/MarkdownSyntax.md).
MARKDOWN_RULES = """Markdown rules:
- Paragraphs: write each paragraph on one line, joining the lines the page broke it into as its script wants (directly for Japanese and Chinese, with a space for scripts that separate words with spaces, keeping a hyphen the author wrote). Separate paragraphs with a blank line.
- Headings: write every heading, including the document's title and every chapter or section title, as a level 2 heading (`## `), whatever its size or numbering on the page.
- Figures: the red boxes with an id number drawn on the page image are the figures. Do not transcribe anything inside a red box.
  - Place each figure of your page exactly once, as a paragraph of its own, where it falls in the reading order: ![caption](figure:ID), with ID the number on its box.
  - Put the figure's caption (for example "Figure 2: ...") as the alt text, and do not write the caption again as body text. Write ![](figure:ID) for a figure that has no caption.
  - The boxes and id labels are not part of the document: never transcribe them as text.
- Math: write every mathematical expression in KaTeX-compatible LaTeX, `$...$` inline and `$$...$$` for a display equation, which goes on lines of its own.
- Tables: write each table as a GFM pipe table, header row included. Repeat a merged cell's content in every cell it spans.
- Code: write source code and pseudocode as a fenced code block.
- Footnotes: write the mark in the body as [^n], and the note itself as a paragraph of its own, `[^n]: note text`, where the note is printed. Use the printed mark as n (for example [^1] or [^*]).
- Sidenotes: text printed in the margin next to the body goes in a sidenote block, placed right after the paragraph it sits beside:
  :::sidenote
  sidenote text
  :::
- Columns: a box, sidebar, or column set apart from the main text goes in a column block, placed where it stands in the reading order:
  :::column
  column text, in the Markdown above
  :::
- Your output must be complete Markdown on its own: close every block you open with a ::: line before your output ends, even when the box carries on past your page, and when your page starts in the middle of a box, open its block again at the start. Never nest one block inside another.
- Never put a figure, footnote, sidenote, or column inside a paragraph: when one is printed in the middle of a paragraph, write the whole paragraph first and the block after it.
- Do not write page numbers, running heads, or running footers: the chapter or section title repeated at the top or bottom of every page is a running head, not a heading.
"""

# What to write, and what not to.
TRANSCRIPTION_RULES = """Transcription rules:
- Output only the Markdown itself: no preamble, no explanation, no code fence around it.
- Follow the document's reading order, multi-column and vertical (tategaki) layouts included.
- Keep the text in its own language. Never translate, paraphrase, or summarize.
- Reproduce the text verbatim, including punctuation, casing, and numbers.
- Do not invent, complete, or correct text that is unclear or cut off; transcribe only what is visible. The page may begin or end in the middle of a sentence: transcribe it as it is, without finishing or leaving out the broken sentence.
"""

# How a page says that its text runs over a page turn (see Docs/MarkdownSyntax.md).
CONTINUATION_RULES = """Page turn rules: the document is transcribed page by page, and the pages are joined afterwards. Say where your page's text runs over a page turn, judging from your page image alone:
- Start your output with <!--continues-previous--> when the first text of the page is the middle of a paragraph begun on the previous page: it starts in the middle of a sentence, or without the indent or spacing the document opens its paragraphs with.
- End your output with <!--continued-by-next--> when the last paragraph of the page runs on onto the next page: it stops in the middle of a sentence, or its last line runs to the end of the line with no sentence-ending punctuation.
- This holds inside a sidenote or column too: keep the block complete as usual (open it again at the start, close it at the end), and put <!--continues-previous--> before its opening line or <!--continued-by-next--> after its closing line.
- Otherwise, do not write either marker. Never write any other page marker.
"""

PROMPT = f"""You are a highly precise OCR engine. You are given one page image of a document, and transcribe it into Markdown.

{TRANSCRIPTION_RULES}
{MARKDOWN_RULES}
{CONTINUATION_RULES}"""

JOIN_PROMPT = """Two consecutive pages of a document were transcribed separately. You are given the end of one page in <end_of_page> and the start of the next page in <start_of_next_page>.

Decide whether the start of the next page continues the same paragraph as the end of the page: the paragraph runs over the page turn, as when a sentence is cut in the middle.

Answer with exactly one word: join if it is one paragraph, break if they are separate paragraphs."""
