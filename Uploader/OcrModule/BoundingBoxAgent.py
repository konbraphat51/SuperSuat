from pydantic import BaseModel
from PIL.Image import Image
from .LlmService import LlmAgent, pil_to_base64

class BoundingBox(BaseModel):
    x: int
    y: int
    width: int
    height: int

class BoundingBoxAgent(LlmAgent):
    def generate_bounding_box(
        self,
        image_data: Image,
        order: str
    ) -> BoundingBox:
        messages = [
            {
                "role": "system",
                "content": "You are an AI agent that generates a bounding box for an image ordered"
            },
            {
                "role": "tool",
                "content": {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{pil_to_base64(image_data)}",
                        "detail": "auto"
                    }
                }
            },
            {
                "role": "user",
                "content": f"Order: {order}"
            }
        ]
        response = self.generate_response_in_format[BoundingBox](messages)
        return response
