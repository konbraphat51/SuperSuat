1. Detect the figure regions with a layout / bounding-box model

- DocLayoutYolo, Yomitoku or PpStructure can be selected as the model
- Draw each detected figure's bounding box and its unique ID onto the page image
- Only figures (figure / image / chart) are detected. Tables and formulas are written out in Markdown by the LLM
- The Blocked pipeline's `Blocker` is left as it is; MdWriter has a figure-only `FigureDetector` of its own

2. Hand the page images to an LLM and have it convert them into Markdown

- Each request has the LLM transcribe one page only
  1. First half: the odd pages (the 1st, 3rd, 5th, … page; even indices, counting from 0) are each given to the LLM on their own to transcribe (in parallel)
  2. Second half: the even pages (the 2nd, 4th, … page) are given to the LLM with the Markdown of the pages either side (from step 1), to be transcribed as the fill between them (in parallel)
  - In the second half, the only image sent is the target page's; the neighbouring pages are sent as Markdown only
  - A second-half page writes its output so that "previous page + its output + next page" reads as one document. Where a paragraph runs over a page turn, it says so with a continuation marker
- Define special syntax for footnotes, sidenotes, columns and the like, and have the LLM use it ([MarkdownSyntax.md](MarkdownSyntax.md))
  - Footnotes in GFM style (`[^n]` / `[^n]: …`), sidenotes and columns as `:::sidenote` / `:::column` blocks
  - `<!--page:N-->` is put before each page's Markdown (by the stitching, not the LLM), which records the pages a block is on
- Every heading is treated as level 2 (each page is written independently, so their hierarchies cannot be matched up)

3. Parse the stitched Markdown into an `OcrResult`

The entry point running it all: [MdWriterOcr.md](MdWriterOcr.md)

日本語版: [Plan.md](Plan.md)
