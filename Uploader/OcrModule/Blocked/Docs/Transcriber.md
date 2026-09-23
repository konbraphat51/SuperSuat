# Transcriber

Step 2 of the blocked OCR pipeline (see [Plan.md](Plan.md)): each `TEXT` block found
by a `Blocker` is cropped from its page and OCR'd in isolation, one block at a time.

日本語版: [Transcriber.ja.md](Transcriber.ja.md)

## Structure

```mermaid
classDiagram
    class Transcriber {
        <<abstract>>
        +transcribe(all_pages: list[Image], blocker_result: BlockerResult) TranscriptionResult
        #_extract_block_image(page: Image, block: Block) Image
        #_ocr_block_image(block_image: Image) str*
    }
    class YomitokuTranscriber {
        -_device: str
        -_recognizer: TextRecognizer
        +default_device() str
        #_ocr_block_image(block_image: Image) str
    }
    class TranscriptionResult {
        +transcriptions: list[TranscriptionBlock]
    }
    class TranscriptionBlock {
        +block_id: int
        +text: str
    }
    Transcriber <|-- YomitokuTranscriber
    Transcriber ..> TranscriptionResult
    TranscriptionResult *-- TranscriptionBlock
```

`Transcriber` implements `transcribe()` as a template method: a subclass only reads
the text of one already-cropped block image — `_ocr_block_image()` — while the base
class handles filtering to `TEXT` blocks, cropping each one out of its page, and
assembling the `TranscriptionResult`.

A page's blocks are read one after another, but `MAX_PARALLEL_PAGES` pages are read
at once. The transcriptions come back in block order whatever order the pages
finished in. A subclass whose model does not take being called from several threads
at once lowers that number.

```mermaid
sequenceDiagram
    participant Caller
    participant Transcriber
    participant Subclass
    participant OcrModel
    Caller->>Transcriber: transcribe(all_pages, blocker_result)
    Transcriber->>Transcriber: group the TEXT blocks by page, dropping the rest
    par up to MAX_PARALLEL_PAGES pages at once
        loop each block of the page
            Transcriber->>Transcriber: crop block_image from all_pages[block.page_index]
            Transcriber->>Subclass: _ocr_text_block_image(block_image)
            Subclass->>OcrModel: recognize
            OcrModel-->>Subclass: text
            Subclass-->>Transcriber: text
            Transcriber->>Transcriber: append TranscriptionBlock(block.block_id, text)
        end
    end
    Transcriber-->>Caller: TranscriptionResult
```

## Conventions

- Only `TEXT` blocks are transcribed here; `MATH`, `IMAGE`, and `TABLE` blocks are
  left for later pipeline steps.
- Each block is OCR'd on its own crop, not the whole page, so recognition never sees
  neighboring blocks.
- `TranscriptionBlock.block_id` matches the `Block.block_id` it was cropped from, so
  transcriptions can be joined back to their blocks by that id.

## YomitokuTranscriber

Uses [yomitoku](https://github.com/kotaro-kinoshita/yomitoku)'s `TextRecognizer`
directly, without its text detector: since each block image is already an isolated
crop, the whole crop is passed as the recognizer's single polygon (`points=None`).

## Device

`YomitokuTranscriber()` picks `cuda` when a GPU is available and falls back to `cpu`,
the same way `YomitokuBlocker` does (see [Blocker.md](Blocker.md)). Pass `device=` to
force one.
