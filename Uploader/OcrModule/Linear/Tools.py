from PIL.Image import Image
import base64
from io import BytesIO

class LinearOcrTools:
    def __init__(
        self,
        page_image_data: list[Image],
    ) -> None:
        self.image_data = page_image_data

    def get_page(
        self,
        page_number: int, # 0-indexed
    ) -> str:
        image = self.image_data[page_number]

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

        return f"data:image/png;base64,{base64_image}" 