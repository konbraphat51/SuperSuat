# TestYomitoku setup

A manual test that runs the PDFs in `Test/Manual/Ocr/Sample/` through
`YomitokuBlocker` (layout analysis only) and writes the detected blocks into
`Test/Manual/Blocked/Output/`.

日本語版: [TestYomitoku_setup.md](TestYomitoku_setup.md)

- Models: yomitoku's layout parser + table structure recognizer, run locally
- **Nothing is billed**: no external API is called
- No text is recognized here — only boxes and their types come out

## 1. Python environment

```bash
cd Uploader
uv sync
```

Torch is installed from the CUDA 13.0 wheel index (`[tool.uv.sources]` in
`pyproject.toml`). It bundles the NVIDIA runtime, so the first sync downloads
several GB.

Check that the GPU is usable:

```bash
uv run python -c "import torch; print(torch.cuda.is_available())"
```

`False` only means it runs on the CPU — several times slower, same results.
`--device cpu` forces that explicitly.

## 2. Model weights

Downloaded from Hugging Face Hub on first run and cached in
`~/.cache/huggingface/`. No authentication is needed; an offline machine fails.

## 3. Running

```bash
cd Uploader

# Every PDF in Sample/
uv run python Test/Manual/Blocked/TestYomitoku.py

# One page first
uv run python Test/Manual/Blocked/TestYomitoku.py --max-pages 1

# One PDF, no PNGs
uv run python Test/Manual/Blocked/TestYomitoku.py --pdf tate.pdf --no-render
```

### Options

| Option | Default | Description |
| --- | --- | --- |
| `--pdf NAME` | every PDF in Sample/ | Target PDF, by file name or path. Repeatable |
| `--dpi N` | `200` | Page render resolution |
| `--max-pages N` | all pages | Only read the first N pages of each PDF |
| `--device NAME` | automatic | Force `cuda` or `cpu` |
| `--no-render` | off | Write only the JSON, skipping the check PNGs |

## 4. Output

```
Test/Manual/Blocked/Output/
├── tate.json       # the BlockerResult, as JSON
├── tate_p0.png     # page image with the detected blocks drawn on it
└── tate_p1.png
```

The JSON is a `BlockerResult`: `bounding_box` is `(x, y, width, height)` and
`page_number` is 0-indexed.

```json
{
  "blocks": [
    { "block_type": "text", "page_number": 0, "bounding_box": [120, 340, 800, 460] },
    { "block_type": "table", "page_number": 0, "bounding_box": [130, 900, 780, 300] }
  ]
}
```

In the PNGs each block type has its own outline color (text=blue, math=red,
image=green, table=orange). The number on a box is its position within the page
(top-to-bottom, then left-to-right).

> `block_type` is rarely `math`: the default layout model has no formula category. See
> [Blocker.md](../../../OcrModule/Blocked/Docs/Blocker.md).

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `ModuleNotFoundError: No module named 'OcrModule'` | Not run through `uv run`. Run `uv run python ...` from the `Uploader` directory |
| `torch.cuda.is_available()` is `False` | A CPU torch build is installed. Re-run `uv sync`. If the NVIDIA driver predates CUDA 13.0, point the index in `pyproject.toml` at a matching one (e.g. `cu128`) |
| `CUDA out of memory` | Lower `--dpi`, or run with `--device cpu` |
| Weight download hangs or fails | Check connectivity to Hugging Face Hub; behind a proxy, set `HF_ENDPOINT` / `HTTPS_PROXY` |
