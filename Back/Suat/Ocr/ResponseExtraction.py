from encodings.idna import sace_prefix
from random import sample


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
    
    pages = analyze_result["pages"]
    result["pages"] = []
    for page in pages:
        adding = {}
        adding["width"] = page["width"]
        adding["height"] = page["height"]
        result["pages"].append(adding)

    result["paragraphs"] = []
    for idx, paragraph in enumerate(analyze_result.get("paragraphs", []), start=1):
        adding = paragraph.copy()
        adding["index"] = idx
        result["paragraphs"].append(adding)

    result["figures"] = []
    for idx, figure in enumerate(analyze_result.get("figures", []), start=1):
        adding = figure.copy()
        adding["index"] = idx
        result["figures"].append(adding)

    result["order"] = []
    for section in analyze_result.get("sections", []):
        for element in section.get("elements", []):
            category, element_id = element.split("/")[1:]
            match category:
                case "paragraphs":
                    result["order"].append({
                        "category": "paragraph",
                        "id": int(element_id)-1
                    })
                case "figures":
                    result["order"].append({
                        "category": "figure",
                        "id": int(element_id)
                    })

    return result

if __name__ == "__main__":
    import json
    with open("./sample_data/sample_ocr.json", "r", encoding="utf-8") as f:
        sample_data = json.load(f)
    extracted_data = extract_response_data(sample_data)
    with open("./sample_data/extracted_data.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(extracted_data, indent=2))
