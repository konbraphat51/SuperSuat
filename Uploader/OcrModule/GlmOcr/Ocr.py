from __future__ import annotations

import io
import re
from pathlib import Path

import torch
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

from ..Ocr import (
    Ocr,
    OcrResult,
    OcrResultBlock,
    OcrResultBlockEquation,
    OcrResultBlockFooter,
    OcrResultBlockSection,
    OcrResultBlockTable,
    OcrResultBlockText,
)

_MODEL_ID = "zai-org/GLM-OCR"
_CACHE_DIR = Path(__file__).parent / "cache"

# GLM-OCR task prompts
_PROMPT_TEXT = "Text Recognition:"
_PROMPT_TABLE = "Table Recognition:"
_PROMPT_FORMULA = "Formula Recognition:"


def _pil_from_bytes(data: bytes) -> Image.Image:
    return Image.open(io.BytesIO(data)).convert("RGB")


def _make_messages(image: Image.Image, prompt: str) -> list[dict]:
    return [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        }
    ]


def _parse_output(text: str) -> list[OcrResultBlock]:
    """Parse GLM-OCR text output into OcrResultBlocks."""
    blocks: list[OcrResultBlock] = []
    table_lines: list[str] = []

    def flush_table() -> None:
        if table_lines:
            block = OcrResultBlockTable(block_type="table")
            block.text = "\n".join(table_lines)
            block.caption = ""
            blocks.append(block)
            table_lines.clear()

    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Fenced block equation
        if line == "$$":
            flush_table()
            eq_lines: list[str] = []
            i += 1
            while i < len(lines) and lines[i].strip() != "$$":
                eq_lines.append(lines[i])
                i += 1
            block = OcrResultBlockEquation(block_type="equation")
            block.text = "\n".join(eq_lines).strip()
            block.caption = ""
            blocks.append(block)
            i += 1
            continue

        # Inline $$...$$
        if line.startswith("$$") and line.endswith("$$") and len(line) > 4:
            flush_table()
            block = OcrResultBlockEquation(block_type="equation")
            block.text = line[2:-2].strip()
            block.caption = ""
            blocks.append(block)
            i += 1
            continue

        if not line:
            flush_table()
            i += 1
            continue

        # Heading
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            flush_table()
            block = OcrResultBlockSection(block_type="section")
            block.text = m.group(2).strip()
            block.level = len(m.group(1))
            blocks.append(block)
            i += 1
            continue

        # Table row
        if line.startswith("|"):
            table_lines.append(line)
            i += 1
            continue

        flush_table()
        block = OcrResultBlockText(block_type="text")
        block.text = line
        blocks.append(block)
        i += 1

    flush_table()
    return blocks


class GlmOcrOcr(Ocr):
    """OCR using GLM-OCR (zai-org/GLM-OCR) via HuggingFace transformers."""

    def __init__(self) -> None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.bfloat16 if device == "cuda" else torch.float32
        print(f"  device: {device}, dtype: {dtype}")

        self._processor = AutoProcessor.from_pretrained(
            _MODEL_ID,
            cache_dir=str(_CACHE_DIR),
        )
        self._model = AutoModelForImageTextToText.from_pretrained(
            _MODEL_ID,
            torch_dtype=dtype,
            device_map="auto",
            cache_dir=str(_CACHE_DIR),
        )

    def _generate(self, image: Image.Image, prompt: str) -> str:
        messages = _make_messages(image, prompt)
        inputs = self._processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self._model.device)

        with torch.no_grad():
            output_ids = self._model.generate(**inputs, max_new_tokens=2048)

        return self._processor.decode(
            output_ids[0][inputs["input_ids"].shape[1] :],
            skip_special_tokens=True,
        )

    def ocr(self, image_data: list[bytes]) -> OcrResult:
        blocks: list[OcrResultBlock] = []

        for data in image_data:
            image = _pil_from_bytes(data)
            text = self._generate(image, _PROMPT_TEXT)
            blocks.extend(_parse_output(text))

        result = OcrResult()
        result.blocks = blocks
        return result
