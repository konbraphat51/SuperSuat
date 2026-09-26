# TestLeveler setup

A manual test that runs saved OCR results (`Input/<stem>.json`) through
`OcrResultLeveler`, and writes the document tree nested by its headings, an outline of
the headings, and the token usage and cost into `Test/Manual/Leveler/Output/<run name>/`
(the model id unless `--run-name` is given).

日本語版: [TestLeveler_setup.md](TestLeveler_setup.md)

- The OpenAI API is really called, so **this is billed**
- The page images are rendered again from `Test/Manual/Ocr/Sample/<stem>.pdf`, at the
  DPI `Input/` was made at (200)

## 1. Input

`Input/` holds the sample PDFs as read by
[TestMdWriter.py](../Ocr/MdWriter/TestMdWriter.py). They are MdWriter's output, so every
heading sits one level deep. Seaman, shido_math and tate were made with the command
below; Probability (284 pages, with a table of contents for the whole book and one per
chapter) is a copy of the all-page run in `Output/doclayout/gpt-6-luna/`.

```bash
uv run python Test/Manual/Ocr/MdWriter/TestMdWriter.py --detector yomitoku --provider openai --model gpt-6-sol --run-name leveler-input
```

| File | Content |
| --- | --- |
| `<stem>.json` | The parsed `OcrResult`, the leveler's input |
| `<stem>.md` | The Markdown the model wrote, to read the headings in |

Making the input again changes the `block_index` of the headings, so `GroundTruth/` has
to be written again too. Only the pages the leveler asks for are rendered, so a long
document does not fill the memory.

## 2. Run

With `OPENAI_API_KEY` in `Uploader/.env`:

```bash
cd Uploader

# every document in Input, on gpt-6-sol
uv run python Test/Manual/Leveler/TestLeveler.py

# one document, on another model
uv run python Test/Manual/Leveler/TestLeveler.py --input shido_math --model gpt-6-luna
```

| Option | Default | Description |
| --- | --- | --- |
| `--input STEM` | every document in Input | The `Input/<stem>.json` to run. Repeatable |
| `--model ID` | `gpt-6-sol` | OpenAI model id |
| `--reasoning-effort LEVEL` | the model's default | Reasoning effort |
| `--max-tokens N` | `16000` | Most tokens in one answer, reasoning included |
| `--dpi N` | `200` | Page image resolution; keep it as `Input/` was made at |
| `--run-name NAME` | the model id | Output folder under `Output/` |
| `--log-level LEVEL` | `INFO` | Logging detail |
| `--log-file PATH` | `Output/TestLeveler.log` | Where the log goes, overwritten each run |

## 3. Output and scoring

```
Test/Manual/Leveler/Output/
├── TestLeveler.log
└── gpt-6-sol/
    ├── shido_math.json         # the nested OcrResult
    ├── shido_math.outline.txt  # the headings indented by level, and the score
    └── shido_math.usage.txt    # requests, page images, tokens and cost
```

Each outline line reads `[block_index] p<page> L<level> heading`. The level is the depth
in the output tree, so a level the model skips (1 → 3) closes up (1 → 2).

Where `GroundTruth/<stem>.json` exists, its `levels` (`block_index` → the level as
printed) are closed up into depths as the output is, and compared with it. A line that
differs from it is marked `<-- expected N`. A heading whose level is `null` (the
`Example` headings of Probability, or math taken for a heading) is not scored. The
`notes` of each file say what the levels were judged by.

The `requests` line of `usage.txt` counts the requests sent, those carrying page images,
and the images. The skeleton request is text only, so the requests with images are the
ones that decided the headings the text left open.

| Metric | Meaning |
| --- | --- |
| `levels` | The share of headings at the right depth |
| `parents` | The share of headings under the right heading. Not lowered when the whole tree is one level off |
