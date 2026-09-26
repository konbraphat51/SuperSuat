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

`Input/` holds the three sample PDFs as read by
[TestMdWriter.py](../Ocr/MdWriter/TestMdWriter.py). They are MdWriter's output, so every
heading sits one level deep.

```bash
uv run python Test/Manual/Ocr/MdWriter/TestMdWriter.py --detector yomitoku --provider openai --model gpt-6-sol --run-name leveler-input
```

| File | Content |
| --- | --- |
| `<stem>.json` | The parsed `OcrResult`, the leveler's input |
| `<stem>.md` | The Markdown the model wrote, to read the headings in |

Making the input again changes the `block_index` of the headings, so `GroundTruth/` has
to be written again too.

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
    └── shido_math.usage.txt    # tokens and cost
```

Each outline line reads `[block_index] p<page> L<level> heading`. The level is the depth
in the output tree, so a level the model skips (1 → 3) closes up (1 → 2).

Where `GroundTruth/<stem>.json` exists, the result is compared with its `levels`
(`block_index` → the right depth). A line that differs from it is marked
`<-- expected N`.

| Metric | Meaning |
| --- | --- |
| `levels` | The share of headings at the right depth |
| `parents` | The share of headings under the right heading. Not lowered when the whole tree is one level off |
