from __future__ import annotations
from typing import Any


class Paragraph:
    def __init__(
        self,
        polygon: list[float],
        role: str,
        content: str,
        index: int,
    ) -> None:
        self.polygon = polygon
        self.role = role
        self.content = content
        self.paragraph_index = index  # 0-indexed

    def to_dict(self) -> dict[str, Any]:
        return {
            "polygon": self.polygon,
            "role": self.role,
            "content": self.content,
            "paragraph_index": self.paragraph_index,
        }


class Page:
    def __init__(
        self,
        number: int,
        width: float,
        height: float
    ) -> None:
        self.number = number
        self.width = width
        self.height = height
        self.paragraphs: list[Paragraph] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "width": self.width,
            "height": self.height,
            "paragraphs": [p.to_dict() for p in self.paragraphs],
        }

def extract_response_data(ocr_response: dict[str, Any]) -> dict[str, Any]:
    """
    Extracts relevant data from the OCR response.

    Args:
        ocr_response (dict): The OCR response containing extracted text and metadata.

    Returns:
        dict: A dictionary containing the extracted text and metadata.
    """
    analyze_result: dict[str, Any] = ocr_response["analyzeResult"]
    
    # pages
    pages_raw = analyze_result["pages"]
    pages: list[Page] = []
    for page_raw in pages_raw:
        page_info = Page(
            number=page_raw["pageNumber"],
            width=page_raw["width"],
            height=page_raw["height"]
        )
        pages.append(page_info)

    # paragraphs
    for idx, paragraph_raw in enumerate(analyze_result["paragraphs"]):
        # 1-indexed
        page_number: int = paragraph_raw["boundingRegions"][0]["pageNumber"]
        
        paragraph_info = Paragraph(
            polygon=paragraph_raw["boundingRegions"][0]["polygon"],
            role=paragraph_raw["role"],
            content=paragraph_raw["content"],
            index=idx
        )

        pages[page_number - 1].paragraphs.append(paragraph_info)

    return {
        "pages": [page.to_dict() for page in pages],
    }

if __name__ == "__main__":
    import json
    with open("./sample_data/sample_ocr.json", "r", encoding="utf-8") as f:
        sample_data = json.load(f)
    extracted_data = extract_response_data(sample_data)
    with open("./sample_data/extracted_data.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(extracted_data, indent=2))
