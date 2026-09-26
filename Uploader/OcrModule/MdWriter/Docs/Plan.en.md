1. Detect the figure regions with a layout / bounding-box model

- DocLayoutYolo, Yomitoku or PpStructure can be selected as the model
- Draw each detected figure's bounding box and its unique ID onto the page image
- Only figures (figure / image / chart) are detected. Tables and formulas are written out in Markdown by the LLM
- The Blocked pipeline's `Blocker` is left as it is; MdWriter has a figure-only `FigureDetector` of its own

2. Hand the page images to an LLM and have it convert them into Markdown

- Each request has the LLM transcribe one page only, every page at once in a single pass
  - Each page says with continuation markers whether its start continues the previous page's paragraph and whether its end runs on, judging from its own image
  - Only where two neighbouring pages disagree is the LLM given the paragraphs either side, as text only, to decide
  - (This was a two-pass scheme before: the odd pages first, then the even pages filled in with the Markdown either side. Waiting on the first pass made it slower, and it decided the joins about the same, so it became one pass.)
- Optionally, each page's text as read by a conventional OCR such as Yomitoku is given to the LLM as a reference
  - The characters are taken from the reference, the structure from the image
  - A page that agrees too little with its reference (the F1 of their character bigrams) is written again by a stronger model
- When the LLM finds a figure box wrong, it calls the `correct_figures` tool; within the call a grounding model (Qwen3-VL on Bedrock) redraws the page's boxes, and the page is written against them
- Define special syntax for footnotes, sidenotes, columns and the like, and have the LLM use it ([MarkdownSyntax.md](MarkdownSyntax.md))
  - Footnotes in GFM style (`[^n]` / `[^n]: …`), sidenotes and columns as `:::sidenote` / `:::column` blocks
  - A table of contents as a `:::toc` block of `- number | title | page` entries, nested by indentation
  - `<!--page:N-->` is put before each page's Markdown (by the stitching, not the LLM), which records the pages a block is on
- Every heading is treated as level 2 (each page is written independently, so their hierarchies cannot be matched up)

3. Parse the stitched Markdown into an `OcrResult`

The entry point running it all: [MdWriterOcr.md](MdWriterOcr.md)

日本語版: [Plan.md](Plan.md)
