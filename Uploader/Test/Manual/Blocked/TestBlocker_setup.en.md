# TestBlocker setup

A manual test that runs the PDFs in `Test/Manual/Ocr/Sample/` through the
`Blocker` implementations (layout analysis only) and writes the detected blocks
into `Test/Manual/Blocked/Output/<blocker>/`.

日本語版: [TestBlocker_setup.md](TestBlocker_setup.md)

- Blockers: `yomitoku`, `doclayout` (DocLayout-YOLO), `ppstructure` (PP-StructureV3)
- **Nothing is billed**: every model runs locally, no external API is called
- No text is recognized here — only boxes and their types come out

## 1. Python environment

```bash
cd Uploader
uv sync
```

Torch comes from the CUDA 13.0 wheel index and paddle from the CUDA 12.9 one
(`[tool.uv.sources]` in `pyproject.toml`). Both bundle their CUDA runtime, so
the first sync downloads several GB.

Check that the GPUs are usable:

```bash
uv run python -c "import torch; print(torch.cuda.is_available())"
uv run python -c "import paddle; print(paddle.device.cuda.device_count())"
```

`False` / `0` only means it runs on the CPU — several times slower, same
results. `--device cpu` forces that explicitly.

## 2. Model weights

Downloaded on first run and cached: yomitoku and DocLayout-YOLO in
`~/.cache/huggingface/`, PP-DocLayout in `~/.paddlex/official_models/`. No
authentication is needed; an offline machine fails.

## 3. Running

```bash
cd Uploader

# Every blocker over every PDF in Sample/
uv run python Test/Manual/Blocked/TestBlocker.py

# One blocker, one page
uv run python Test/Manual/Blocked/TestBlocker.py --blocker doclayout --max-pages 1

# One blocker, one PDF, no PNGs
uv run python Test/Manual/Blocked/TestBlocker.py --blocker ppstructure --pdf tate.pdf --no-render
```

### Options

| Option | Default | Description |
| --- | --- | --- |
| `--blocker NAME` | every blocker | `yomitoku`, `doclayout`, or `ppstructure`. Repeatable |
| `--pdf NAME` | every PDF in Sample/ | Target PDF, by file name or path. Repeatable |
| `--dpi N` | `200` | Page render resolution |
| `--max-pages N` | all pages | Only read the first N pages of each PDF |
| `--device NAME` | automatic | Force a device, named as the chosen blocker names it (`cuda`/`cpu`, or `gpu`/`cpu` for `ppstructure`) |
| `--no-render` | off | Write only the JSON, skipping the check PNGs |

## 4. Output

```
Test/Manual/Blocked/Output/
├── doclayout/
│   ├── tate.json       # the BlockerResult, as JSON
│   ├── tate_p0.png     # page image with the detected blocks drawn on it
│   └── tate_p1.png
├── ppstructure/
└── yomitoku/
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

> With `yomitoku`, `block_type` is rarely `math`: its default layout model has no
> formula category. The other two blockers do have one. See
> [Blocker.md](../../../OcrModule/Blocked/Docs/Blocker.md).

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `ModuleNotFoundError: No module named 'OcrModule'` | Not run through `uv run`. Run `uv run python ...` from the `Uploader` directory |
| `torch.cuda.is_available()` is `False` | A CPU torch build is installed. Re-run `uv sync`. If the NVIDIA driver predates CUDA 13.0, point the index in `pyproject.toml` at a matching one (e.g. `cu128`) |
| `OSError: [WinError 127] … Error loading "torch\lib\shm.dll"` | Paddle was imported before torch. Import torch first, as `PpStructure.py` does |
| `CUDA out of memory` | Lower `--dpi`, or run with `--device cpu` |
| Weight download hangs or fails | Check connectivity to Hugging Face Hub and to the PaddleX model host; behind a proxy, set `HF_ENDPOINT` / `HTTPS_PROXY` |
