# MdWriterOcr

The MdWriter OCR pipeline (see [Plan.en.md](Plan.en.md)). A layout model finds only the
figures, which are drawn onto the pages with their ids; a multimodal model then writes
the pages out as Markdown, one page per request, placing each figure by id, and the
Markdown is read into an `OcrResult`. A page between two others is written last, with
the Markdown of both in view, so that text running over a page turn joins into one
paragraph.

日本語版: [MdWriterOcr.ja.md](MdWriterOcr.ja.md)

## Structure

```mermaid
classDiagram
    class Ocr {
        <<abstract>>
        +ocr(all_page_images: list[Image]) OcrResult*
    }
    class MdWriterOcr {
        +figure_detector: FigureDetector
        +transcriber: PageTranscriber
        +max_parallel_pages: int
        +renderer: BlockRenderer
        +ocr(all_page_images: list[Image]) OcrResult
        +write_markdown(all_page_images: list[Image]) MarkdownDraft
    }
    class FigureDetector {
        <<abstract>>
        +MAX_PARALLEL_PAGES: int
        +detect(pages: list[Image]) list[DetectedFigure]
        #_detect_page_figures(page: Image) list[tuple]*
    }
    class DocLayoutYoloFigureDetector
    class YomitokuFigureDetector
    class PpStructureFigureDetector
    class PageTranscriber {
        +model: BaseChatModel
        +max_attempt_count: int
        +write(task, rendered_pages, figures) str
        +fill(task, rendered_pages, figures, previous_markdown, next_markdown) str
    }
    class BlockRenderer {
        +render_page(page: Image, blocks: Sequence[BoxedBlock]) Image
    }
    class DetectedFigure {
        +block_id: int
        +page_index: int
        +bounding_box: tuple[int, int, int, int]
    }
    class PageTask {
        +page_index: int
        +kind: PageKind
    }
    class MarkdownDraft {
        +markdown: str
        +figures: list[DetectedFigure]
        +rendered_pages: list[Image]
    }
    Ocr <|-- MdWriterOcr
    FigureDetector <|-- DocLayoutYoloFigureDetector
    FigureDetector <|-- YomitokuFigureDetector
    FigureDetector <|-- PpStructureFigureDetector
    MdWriterOcr o-- FigureDetector
    MdWriterOcr o-- PageTranscriber
    MdWriterOcr o-- BlockRenderer
    MdWriterOcr ..> PageTask
    MdWriterOcr ..> MarkdownDraft
    FigureDetector ..> DetectedFigure
    PageTranscriber ..> PageTask
    BlockRenderer ..> DetectedFigure : as BoxedBlock
```

The remaining stages are plain functions, each in a module of its own:

| Module | Function | Responsibility |
| --- | --- | --- |
| [Transcriber/prompt.py](../Transcriber/prompt.py) | `WRITE_PROMPT`, `FILL_PROMPT` | What the model is told, the [Markdown syntax](MarkdownSyntax.md) included |
| [MarkdownValidator.py](../MarkdownValidator.py) | `validate_page_output` | What is wrong with an answer, as lines the model can act on |
| [Markers.py](../Markers.py) | `strip_page_markers`, `split_continuation`, … | Finding and taking out the page and continuation markers |
| [Containers.py](../Containers.py) | `fence_problems`, `closing_container`, … | Checking the `:::` fences, and joining a box split at a page boundary |
| [Stitcher.py](../Stitcher.py) | `stitch` | The parts joined into one document |
| [MarkdownParser.py](../MarkdownParser.py) | `parse_markdown` | The document read into the `OcrResult` tree |

Shared with the rest of the OCR module: `run_parallel` ([PageParallel.py](../../Blocked/PageParallel.py)),
`BlockRenderer` ([BlockRenderer.py](../../Blocked/Blocker/BlockRenderer.py)), `join_texts` /
`join_separator` ([TextJoin.py](../../TextJoin.py)), the message helpers of
[LlmHelper.py](../../LlmHelper.py), and `OcrResultSection.recompute_existing_pages`.

## Figure detection

`FigureDetector.detect()` is a template method, as in the Blocked pipeline's `Blocker`: a
subclass only returns the boxes of the figures of one page, and the base class detects
`MAX_PARALLEL_PAGES` pages at once, sorts each page top-to-bottom, and numbers the
figures across the document once every page is in, so the ids never depend on which
page finished first.

Each detector reuses the loading and box conversion of the Blocker for the same model,
and keeps only the classes that are figures:

| Detector | Kept |
| --- | --- |
| `DocLayoutYoloFigureDetector` | class `figure` |
| `YomitokuFigureDetector` | `layout.figures` |
| `PpStructureFigureDetector` | labels `image` and `chart` (not `header_image` / `footer_image`, which are logos) |

`PpStructureFigureDetector` sets `MAX_PARALLEL_PAGES = 1`: the PaddleX predictor mixes up
the results of pages predicted from several threads at once, handing one page's figures to
another.

Tables and formulas are not detected: the model writes them as Markdown tables and KaTeX.
The detectors live under `MdWriter/` rather than as an option of the `Blocker`, which
deliberately drops every class label.

## Passes

Every page is one request. The pages at even indices (the 1st, 3rd, 5th, … page) are the
*write* pages: the first pass sends each of them on its own. The pages between them are
the *fill* pages: the second pass sends each with the Markdown the write pages either
side of it came back as. With 5 pages:

```mermaid
flowchart LR
    subgraph first["pass 1 (write, in parallel)"]
        p0[0]
        p2[2]
        p4[4]
    end
    subgraph second["pass 2 (fill, in parallel)"]
        p1[1]
        p3[3]
    end
    p0 -. Markdown .-> p1
    p2 -. Markdown .-> p1
    p2 -. Markdown .-> p3
    p4 -. Markdown .-> p3
```

A fill page is sent its own image only; the neighbours are there as text, to show where
their paragraphs break off. A one-page document has no second pass, and a fill page that
ends the document has no next page.

## Flow

```mermaid
sequenceDiagram
    participant Caller
    participant L as MdWriterOcr
    participant D as FigureDetector
    participant R as BlockRenderer
    participant T as PageTranscriber
    participant M as Chat model
    Caller->>L: ocr(pages)
    L->>D: detect(pages)
    D-->>L: figures
    L->>R: render_page(page, figures of the page), per page
    R-->>L: rendered pages
    par every write page
        L->>T: write(task, rendered, figures)
        loop until the answer checks out, at most 3 times
            T->>M: the page, labeled with its figures
            M-->>T: Markdown
            T->>T: validate_page_output
        end
        T-->>L: Markdown of the page
    end
    par every fill page
        L->>T: fill(task, rendered, figures, previous, next)
        loop until the answer checks out, at most 3 times
            T->>M: previous page's Markdown, the page, next page's Markdown
            M-->>T: Markdown of the page
            T->>T: validate_page_output
        end
        T-->>L: Markdown of the page
    end
    L->>L: stitch(parts in page order)
    L->>L: parse_markdown(markdown, figures)
    L-->>Caller: OcrResult
```

Both passes go through `run_parallel`, `max_parallel_pages` pages at a time. The first
failure ends the run: a page that still does not check out after `max_attempt_count`
attempts raises `RuntimeError`. Every request carries `page_index` and `page_kind` in its
run metadata, so a callback can tell which page a request, and its token usage, was for.

A fill page is told that its answer goes verbatim between its two neighbours, so it
writes the rest of a paragraph the previous page broke off rather than starting it again,
and says so with `<!--continues-previous-->`; a paragraph of its own that the next page
carries on is marked with `<!--continued-by-next-->`. The model writes no page markers:
the stitcher puts `<!--page:N-->` before every page's Markdown (any the model wrote are
taken out first), and joins the two halves of a paragraph at a continuation marker — with
a space only between two ASCII characters, as `join_texts` does — and blank lines
everywhere else. Two write pages are never next to each other, so every join is decided
by the fill page between them.

`write_markdown()` stops before parsing and returns the Markdown with the figures and the
rendered pages, for a caller that wants to look at them.

## Tests

- Unit tests in [Test/Unit/MdWriter/](../../../Test/Unit/MdWriter/): the markers and fences, the validator, the stitcher, the parser, the transcriber against a
  scripted fake model (retry and its limit included), and the whole pipeline against a
  fake detector and a fake model that answers from the request.
- A manual run over the sample PDFs, with a real detector and model, reporting every
  page's tokens and cost:
  [TestMdWriter_setup.en.md](../../../Test/Manual/MdWriter/TestMdWriter_setup.en.md).

```bash
cd Uploader
uv run pytest
uv run mypy          # strict, over MdWriter
```
