1. Split the page elements into blocks with a layout analysis model (bounding boxes only)
2. (in parallel) Infer each block type and the reading order page by page with an LLM, then rank the headings into a hierarchy in one pass ([StructureOrganizer.md](StructureOrganizer.md))
3. (in parallel) Read the text of each block with an OCR model. The block types are settled by then, so a table is read as a table and a figure is not read at all ([Transcriber.md](Transcriber.md))

The entry point running all three: [BlockedOcr.md](BlockedOcr.md)

日本語版: [Plan.md](Plan.md)
