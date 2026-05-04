# Uploader

## Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- NVIDIA GPU (CUDA 12.6 compatible driver)

## Setup

```bash
uv sync
```

## Run

```bash
uv run python main.py
```

## OCR model cache

Models are downloaded automatically on first run and stored in `OcrModule/PaddleOcrVl/cache/`.

## Manual test (OCR)

```bash
uv run python Test/Manual/Ocr/test_paddle_ocr_vl.py
```
