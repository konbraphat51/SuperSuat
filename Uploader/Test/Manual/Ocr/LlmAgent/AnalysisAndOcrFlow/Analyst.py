import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# project root
ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

# Set bearer token for Bedrock short-term API key before importing clients
_api_key = os.environ.get("AWS_BEDROCK_SHORT_API_KEY", "")
if _api_key:
    os.environ["AWS_BEARER_TOKEN_BEDROCK"] = _api_key

import fitz  # pymupdf
from PIL import Image

from OcrModule.LlmAgent.AnalysisAndOcrFlow.Nodes.Analyst import (
    first_analyst_node,
)
from OcrModule.LlmAgent.AnalysisAndOcrFlow.States import AnalysisState

PDF_PATH = ROOT / "Test" / "Manual" / "Ocr" / "Sample" / "shido_math.pdf"


def pdf_to_images(pdf_path: Path) -> list:
    doc = fitz.open(str(pdf_path))
    images = []
    for page in doc:
        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)
    doc.close()
    return images


async def main() -> None:
    print(f"Loading PDF: {PDF_PATH}")
    images = pdf_to_images(PDF_PATH)
    print(f"Pages loaded: {len(images)}")

    state: AnalysisState = {
        "images": images,
        "heading_style_map": {},
        "ocr_rules": "",
        "messages": [],
    }

    print("Running first_analyst_node...")
    result = await first_analyst_node(state)

    print("\n--- heading_style_map ---")
    for level, description in result["heading_style_map"].items():
        print(f"  Level {level}: {description}")

    print("\n--- ocr_rules ---")
    print(result["ocr_rules"])


if __name__ == "__main__":
    asyncio.run(main())
