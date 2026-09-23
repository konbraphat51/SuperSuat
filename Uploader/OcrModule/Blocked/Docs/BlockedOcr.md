# BlockedOcr

The entry point of the blocked OCR pipeline: it is the `Ocr` implementation that
runs the three stages of [Plan.md](Plan.md) over a document and hands back the
`OcrResult` tree.

日本語版: [BlockedOcr.ja.md](BlockedOcr.ja.md)

## Structure

```mermaid
classDiagram
    class Ocr {
        <<abstract>>
        +ocr(all_page_images: list[Image]) OcrResult*
    }
    class BlockedOcr {
        -blocker: Blocker
        -transcriber: Transcriber
        -organizer: Organizer
        -block_renderer: BlockRenderer
        +ocr(all_page_images: list[Image]) OcrResult
    }
    class Blocker {
        <<abstract>>
        +block(pages) BlockerResult
    }
    class Transcriber {
        <<abstract>>
        +transcribe(all_pages, blocker_result) TranscriptionResult
    }
    class BlockRenderer {
        +render(pages, blocker_result) list[Image]
    }
    class Organizer {
        +organize(all_page_images, all_page_images_rendered, blocker_result, transcription_result) OcrResult
    }
    Ocr <|-- BlockedOcr
    BlockedOcr o-- Blocker
    BlockedOcr o-- Transcriber
    BlockedOcr o-- Organizer
    BlockedOcr *-- BlockRenderer
```

Each stage is handed in already built, so which model does the work is the caller's
choice: a local layout model with a remote chat model, or a cheaper mix, is the same
pipeline. `BlockRenderer` is the exception and is built here - it has no model and no
choice to make.

## Run

```mermaid
sequenceDiagram
    participant Caller
    participant BlockedOcr
    participant Blocker
    participant Transcriber
    participant BlockRenderer
    participant Organizer
    Caller->>BlockedOcr: ocr(all_page_images)
    BlockedOcr->>Blocker: block(all_page_images)
    Blocker-->>BlockedOcr: BlockerResult
    BlockedOcr->>Transcriber: transcribe(all_page_images, blocker_result)
    Transcriber-->>BlockedOcr: TranscriptionResult
    BlockedOcr->>BlockRenderer: render(all_page_images, blocker_result)
    BlockRenderer-->>BlockedOcr: one annotated page per page
    BlockedOcr->>Organizer: organize(images, rendered images, blocks, transcriptions)
    Organizer-->>BlockedOcr: OcrResult
    BlockedOcr-->>Caller: OcrResult
```

The stages run one after another, each one over the whole document: every stage needs
all of the previous one's output. Pages are worked on several at a time *inside*
`Blocker`, `Transcriber` and the organizer's `Classifier`, which is where the
parallelism of this pipeline lives (see [Blocker.md](Blocker.md)).

The annotated pages are rendered here rather than in the organizer: they exist so the
organizer's model can tell which block on the page a `block_id` names, and rendering
them once for the whole document is cheaper than once per page scan.

## Conventions

- The page images are never modified: `BlockRenderer` draws on copies, and every stage
  reads `all_page_images` as given.
- Every page held in a variable is 0-indexed, as everywhere else in the OCR module.
