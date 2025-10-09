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
        self.items: list[Item] = []

class Item:
    pass

class Paragraph(Item):
    def __init__(
        self,
        polygon: list[float],
        role: str,
        content: str,
        page: int,
    ) -> None:
        self.type = "paragraph"
        self.polygon = polygon
        self.role = role
        self.content = content
        self.page = page    # 1-indexed

class Figure(Item):
    def __init__(
        self,
        index_figure: int,
        polygon: list[float],
        caption: str,
        page: int,
        elements: list[str] = []
    ) -> None:
        self.type = "figure"
        self.index_figure = index_figure
        self.polygon = polygon
        self.caption = caption
        self.page = page    # 1-indexed
        self.paragraph_indices = self.convert_elements(elements)

    def convert_elements(self, elements: list[str]) -> list[int]:
        # element ref -> paragraph index
        paragraph_indices: list[int] = []
        for element in elements:
            if element.startswith("/paragraphs/"):
                paragraph_index = int(element.split("/")[2])
                paragraph_indices.append(paragraph_index)

        return paragraph_indices

def extract_response_data(ocr_response: dict) -> dict:
    """
    Extracts relevant data from the OCR response.

    Args:
        ocr_response (dict): The OCR response containing extracted text and metadata.

    Returns:
        dict: A dictionary containing the extracted text and metadata.
    """
    result = {}

    analyze_result = ocr_response["analyzeResult"]
    
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
    paragraphs: list[Paragraph] = []
    for idx, paragraph_raw in enumerate(analyze_result["paragraphs"]):
        paragraph_info = Paragraph(
            polygon=paragraph_raw["boundingRegions"][0]["polygon"],
            role=paragraph_raw["role"],
            content=paragraph_raw["content"],
            page=paragraph_raw["boundingRegions"][0]["pageNumber"]
        )
        paragraphs.append(paragraph_info)

    # figures
    figures: list[Figure] = []
    for idx, figure_raw in enumerate(analyze_result["figures"]):
        figure_info = Figure(
            index_figure=idx,
            polygon=figure_raw["boundingRegions"][0]["polygon"],
            caption=figure_raw.get("caption", ""),
            page=figure_raw["boundingRegions"][0]["pageNumber"]
        )
        figures.append(figure_info)

    

    return result

def 

if __name__ == "__main__":
    import json
    with open("./sample_data/sample_ocr.json", "r", encoding="utf-8") as f:
        sample_data = json.load(f)
    extracted_data = extract_response_data(sample_data)
    with open("./sample_data/extracted_data.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(extracted_data, indent=2))
