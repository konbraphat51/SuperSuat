"""The instructions the model transcribes a page into Markdown with."""

# The Markdown both passes write, and MarkdownParser reads (see Docs/MarkdownSyntax.md).
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

# Common to both passes: what to write, and what not to.
TRANSCRIPTION_RULES = """Transcription rules:
- Output only the Markdown itself: no preamble, no explanation, no code fence around it.
- Follow the document's reading order, multi-column and vertical (tategaki) layouts included.
- Keep the text in its own language. Never translate, paraphrase, or summarize.
- Reproduce the text verbatim, including punctuation, casing, and numbers.
- Do not invent, complete, or correct text that is unclear or cut off; transcribe only what is visible. The page may begin or end in the middle of a sentence: transcribe it as it is, without finishing or leaving out the broken sentence.
"""

WRITE_PROMPT = f"""You are a highly precise OCR engine. You are given one page image of a document, and transcribe it into Markdown.

{TRANSCRIPTION_RULES}
{MARKDOWN_RULES}"""

FILL_PROMPT = f"""You are a highly precise OCR engine. A document is being transcribed into Markdown page by page, and you transcribe one page whose neighbouring pages are already transcribed.

You are given:
- the Markdown of the page right before yours, in <previous_page>;
- the image of your page;
- the Markdown of the page right after yours, in <next_page>, unless yours is the last page.

Your output is inserted verbatim between the two neighbouring pages, so that the previous page, your output, and the next page read as one continuous document.
- If the previous page ends in the middle of a paragraph that carries on onto your page, start your output with <!--continues-previous-->, followed straight away by the rest of that paragraph as your page shows it.
- If your page's last paragraph carries on onto the next page, end your output with <!--continued-by-next-->, right after your page's last text.
- This holds inside a sidenote or column too. When the paragraph that carries on is inside a box, open the same block again right after <!--continues-previous--> (a :::column line, then the rest of the paragraph); and when your last paragraph carries on into a box the next page opens, close your block with ::: as usual, before <!--continued-by-next-->. The two halves of the box are joined into one.
- Otherwise, do not write either marker.
- Transcribe only your own page, from its image: the neighbouring pages are there only to show how the text runs on. Never repeat, rewrite, or correct their text.

{TRANSCRIPTION_RULES}
{MARKDOWN_RULES}"""
