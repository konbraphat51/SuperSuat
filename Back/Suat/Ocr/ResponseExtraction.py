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

    result["paragraphs"] = analyze_result["paragraphs"]

    result["figures"] = analyze_result["figures"]

    return result

if __name__ == "__main__":
    import json
    with open("./sample_data/sample_ocr.json", "r", encoding="utf-8") as f:
        sample_data = json.load(f)
    extracted_data = extract_response_data(sample_data)
    with open("./sample_data/extracted_data.json", "w", encoding="utf-8") as f:
        f.write(json.dumps(extracted_data, indent=2))
