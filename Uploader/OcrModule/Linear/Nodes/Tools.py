import base64
from io import BytesIO
from PIL.Image import Image
from ...OcrSchema import OcrResultSection

def pil_to_base64(img: Image, format: str = "PNG") -> str:
    buffered = BytesIO()
    img.save(buffered, format=format)
    img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_b64

class LinearTools:
    def __init__(
        self,
        all_page_images: list[Image],
        ocr_entire_section: OcrResultSection
    ) -> None:
        self.all_page_images = all_page_images
        self.ocr_entire_section = ocr_entire_section

    def get_page_image(self, page_number: int):
        if page_number < 0 or page_number >= len(self.all_page_images):
            return f"ERROR: Invalid page number. The page number must be between 0 and {len(self.all_page_images) - 1}"

        img = self.all_page_images[page_number]
        img_b64 = pil_to_base64(img)

        return [
            {
                "type": "text",
                "text": f"this is the image of page {page_number}"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_b64}",
                }
            }
        ]
