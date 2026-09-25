1. Detect the figure regions with a layout / bounding-box model

- DocLayoutYolo, Yomitoku or PpStructure can be selected as the model
- Draw each detected figure's bounding box and its unique ID onto the page image
- Only figures (figure / image / chart) are detected. Tables and formulas are written out in Markdown by the LLM
- The Blocked pipeline's `Blocker` is left as it is; MdWriter has a figure-only `FigureDetector` of its own

2. Hand the page images to an LLM and have it convert them into Markdown

- With `BATCH_SIZE` as the batch size,
  1. First, the pages in `[BATCH_SIZE*x, BATCH_SIZE*(x+1)]` (x even) are given to the LLM to transcribe (in parallel)
  2. Then, the pages in `[BATCH_SIZE*x, BATCH_SIZE*(x+1)]` (x odd) are given to the LLM to fill the gaps in the Markdown step 1 returned (in parallel)
  - In step 2, the only Markdown the LLM is given is that of the batches right before and right after the target batch (from step 1).
- The ranges are closed intervals: neighbouring batches share their boundary page
  - An even batch transcribes all of its pages
  - An odd batch transcribes only its inner pages, the ones no even batch covers. The boundary pages are sent as context, so the model can read how the text runs on
  - An odd batch writes its output so that "previous batch + its output + next batch" reads as one document. Where a paragraph runs over a boundary, it says so with a continuation marker
  - `BATCH_SIZE` is 2 or more
- Define special syntax for footnotes, sidenotes, columns and the like, and have the LLM use it ([MarkdownSyntax.md](MarkdownSyntax.md))
  - Footnotes in GFM style (`[^n]` / `[^n]: …`), sidenotes and columns as `:::sidenote` / `:::column` blocks
  - Each page starts with `<!--page:N-->`, which records the pages a block is on
- Every heading is treated as level 2 (each batch is written independently, so their hierarchies cannot be matched up)

3. Parse the stitched Markdown into an `OcrResult`

The entry point running it all: [MdWriterOcr.md](MdWriterOcr.md)

日本語版: [Plan.md](Plan.md)
