"""The instructions the model transcribes a batch of pages into Markdown with."""

# The Markdown both passes write, and MarkdownParser reads (see Docs/MarkdownSyntax.md).
MARKDOWN_RULES = """Markdown rules:
- Page markers: write <!--page:N--> exactly where the content of page N begins, N being the page number given before its image. Every page you transcribe gets exactly one marker, in page order, even a page with no text on it.
  - When a paragraph runs over from one page onto the next, put the next page's marker inside the paragraph, at the exact point the page turns, on the same line: never break the paragraph for it.
- Paragraphs: write each paragraph on one line, joining the lines the page broke it into as its script wants (directly for Japanese and Chinese, with a space for scripts that separate words with spaces, keeping a hyphen the author wrote). Separate paragraphs with a blank line.
- Headings: write every heading, including the document's title and every chapter or section title, as a level 2 heading (`## `), whatever its size or numbering on the page.
- Figures: the red boxes with an id number drawn on the page images are the figures. Do not transcribe anything inside a red box.
  - Place each figure of the pages you transcribe exactly once, as a paragraph of its own, where it falls in the reading order: ![caption](figure:ID), with ID the number on its box.
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
- Never put a figure, footnote, sidenote, or column inside a paragraph: when one is printed in the middle of a paragraph (a page turn included), write the whole paragraph first and the block after it.
- Do not write page numbers, running heads, or running footers.
"""

# Common to both passes: what to write, and what not to.
TRANSCRIPTION_RULES = """Transcription rules:
- Output only the Markdown itself: no preamble, no explanation, no code fence around it.
- Follow the document's reading order, multi-column and vertical (tategaki) layouts included.
- Keep the text in its own language. Never translate, paraphrase, or summarize.
- Reproduce the text verbatim, including punctuation, casing, and numbers.
- Do not invent, complete, or correct text that is unclear or cut off; transcribe only what is visible. A page may begin or end in the middle of a sentence: transcribe it as it is.
"""

WRITE_PROMPT = f"""You are a highly precise OCR engine. You are given consecutive page images of one document, and transcribe every one of them into a single Markdown document.

{TRANSCRIPTION_RULES}
{MARKDOWN_RULES}"""
