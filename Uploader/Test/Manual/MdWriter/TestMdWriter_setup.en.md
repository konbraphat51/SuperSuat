# TestMdWriter setup

A manual test that runs the PDFs in `Test/Manual/Ocr/Sample/` through `MdWriterOcr`
and writes the transcribed Markdown, the parsed document tree, and the page images
with their figures drawn on into `Test/Manual/MdWriter/Output/<detector>/`.

日本語版: [TestMdWriter_setup.md](TestMdWriter_setup.md)

- Figure detection: `doclayout` (DocLayout-YOLO) / `yomitoku` / `ppstructure` (PP-StructureV3), run locally
- Transcription: a multimodal model on the OpenAI API or on Amazon Bedrock
- The API is really called, so **this is billed**. One request carries `BATCH_SIZE + 1`
  page images, so start with `--max-pages 5 --batch-size 2` (three requests)

## 1. Python environment

```bash
cd Uploader
uv sync
```

GPUs and model weights are as in [TestBlocker_setup.en.md](../Blocked/TestBlocker_setup.en.md).

## 2. API keys

Put these in `Uploader/.env` (see `template.env`).

| Variable | Used for |
| --- | --- |
| `OPENAI_API_KEY` | Transcribing on OpenAI |
| `AWS_BEDROCK_SHORT_API_KEY` | Transcribing on Bedrock (how to issue one: [TestLinear_setup.md](../Ocr/TestLinear_setup.md)) |
| `OCR_PROVIDER` | `openai` / `bedrock`. Defaults to `openai` |
| `OCR_MODEL_ID` | Model id. Defaults to one per provider |

## 3. Run

```bash
cd Uploader

# 5 pages only, with BATCH_SIZE=2
uv run python Test/Manual/MdWriter/TestMdWriter.py --pdf shido_math.pdf --detector doclayout --batch-size 2 --max-pages 5

# every sample PDF, with the defaults
uv run python Test/Manual/MdWriter/TestMdWriter.py
```

### Options

| Option | Default | Description |
| --- | --- | --- |
| `--pdf NAME` | every sample PDF | PDF to run, by file name or path. Repeatable |
| `--detector NAME` | `doclayout` | `doclayout` / `yomitoku` / `ppstructure` |
| `--batch-size N` | `4` | Pages apart the batches start. 2 or more |
| `--max-parallel N` | `4` | Most batches sent at once |
| `--max-pages N` | every page | Only read the first N pages of each PDF |
| `--dpi N` | `200` | Page render resolution |
| `--provider NAME` | `OCR_PROVIDER` | `openai` / `bedrock` |
| `--model ID` | `OCR_MODEL_ID` | Model id |
| `--max-tokens N` | `32000` | Most tokens in one answer; large, since one answer writes several pages |
| `--reasoning-effort LEVEL` | `OPENAI_REASONING_EFFORT` | Reasoning depth of an OpenAI reasoning model |
| `--log-level LEVEL` | `INFO` | Log verbosity |
| `--log-file PATH` | `Output/TestMdWriter.log` | Where the log goes (overwritten every run) |

## 4. Output

```
Test/Manual/MdWriter/Output/
├── TestMdWriter.log     # model answers, token usage, validation problems and retries
└── doclayout/
    ├── Seaman.md        # every batch stitched together, page markers included
    ├── Seaman.json      # the parsed OcrResult
    └── Seaman/
        ├── page_0.png   # the page as sent to the model, figure boxes and ids drawn on
        └── ...
```

What to check:

- In the PNGs, only figures carry a box and an id
- In the `.md`, no sentence is repeated or missing around a batch boundary (pages at multiples of `BATCH_SIZE`)
- In the `.json`, `existing_pages` and the figures' `bounding_box` are right
- In the log, whether any `WARNING` shows a retry after a validation problem, and which rule it tripped on

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `RuntimeError: batch N ... did not return usable Markdown` | No answer passed validation in three attempts. See the log's `WARNING`s for why. A smaller `--batch-size` asks less of each request |
| `ValueError: batch_size must be at least 2` | Set `--batch-size` to 2 or more |
| An answer is cut short and fails validation | Raise `--max-tokens`, or lower `--batch-size` |
| `ERROR: OPENAI_API_KEY is not set.` | Put `OPENAI_API_KEY` in `.env`, or use `--provider bedrock` |
