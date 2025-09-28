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
