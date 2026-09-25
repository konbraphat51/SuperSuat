# TestMdWriter setup

A manual test that runs the PDFs in `Test/Manual/Ocr/Sample/` through `MdWriterOcr`
and writes the transcribed Markdown, the parsed document tree, every page's token usage
and cost, and the page images with their figures drawn on into
`Test/Manual/MdWriter/Output/<detector>/<model>/`.

日本語版: [TestMdWriter_setup.md](TestMdWriter_setup.md)

- Figure detection: `doclayout` (DocLayout-YOLO) / `yomitoku` / `ppstructure` (PP-StructureV3), run locally
- Transcription: a multimodal model on the OpenAI API or on Amazon Bedrock
- The API is really called, so **this is billed**. One request carries one page image,
  so start with `--max-pages 5` (five requests, plus any retries)

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

# 5 pages only
uv run python Test/Manual/MdWriter/TestMdWriter.py --pdf shido_math.pdf --detector doclayout --max-pages 5

# gpt-6-sol instead of the default model
uv run python Test/Manual/MdWriter/TestMdWriter.py --detector yomitoku --provider openai --model gpt-6-sol

# every sample PDF, with the defaults
uv run python Test/Manual/MdWriter/TestMdWriter.py
```

### Options

| Option | Default | Description |
| --- | --- | --- |
| `--pdf NAME` | every sample PDF | PDF to run, by file name or path. Repeatable |
| `--detector NAME` | `doclayout` | `doclayout` / `yomitoku` / `ppstructure` |
| `--max-parallel N` | `8` | Most pages sent at once |
| `--max-pages N` | every page | Only read the first N pages of each PDF |
| `--dpi N` | `200` | Page render resolution |
| `--provider NAME` | `OCR_PROVIDER` | `openai` / `bedrock` |
| `--model ID` | `OCR_MODEL_ID` | Model id |
| `--max-tokens N` | `16000` | Most tokens in one answer, reasoning included |
| `--reasoning-effort LEVEL` | `OPENAI_REASONING_EFFORT` | Reasoning depth of an OpenAI reasoning model |
| `--log-level LEVEL` | `INFO` | Log verbosity |
| `--log-file PATH` | `Output/TestMdWriter.log` | Where the log goes (overwritten every run) |

## 4. Output

```
Test/Manual/MdWriter/Output/
├── TestMdWriter.log         # model answers, token usage, validation problems and retries
└── doclayout/
    └── gpt-5.6-luna/
        ├── Seaman.md        # every page stitched together, page markers included
        ├── Seaman.json      # the parsed OcrResult
        ├── Seaman.usage.txt # every page's requests, tokens and cost
        └── Seaman/
            ├── page_0.png   # the page as sent to the model, figure boxes and ids drawn on
            └── ...
```

The usage table is also printed when each PDF is done. `input` counts every input token,
`cached` the part of it read from the cache, and `output` every output token, of which
`reason` went to the model's reasoning; a `reason` above zero is how to tell that the
model's chain of thought is on. The cost is worked out from `UsageCost.PRICING` (USD per
million tokens), and shown only for a model listed there:

| Model | Input | Cached input | Cache writes | Output |
| --- | --- | --- | --- | --- |
| `gpt-6-luna` | $0.10 | $0.01 | $0.125 | $0.50 |
| `gpt-6-sol` | $2.00 | $0.20 | $2.50 | $10.00 |

What to check:

- In the PNGs, only figures carry a box and an id
- In the `.md`, no sentence is repeated or missing around a page turn
- In the `.json`, `existing_pages` and the figures' `bounding_box` are right
- In the log, whether any `WARNING` shows a retry after a validation problem, and which rule it tripped on

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `RuntimeError: page N ... did not return usable Markdown` | No answer passed validation in three attempts. See the log's `WARNING`s for why |
| An answer is cut short and fails validation | Raise `--max-tokens`: reasoning counts towards it |
| `ERROR: OPENAI_API_KEY is not set.` | Put `OPENAI_API_KEY` in `.env`, or use `--provider bedrock` |
