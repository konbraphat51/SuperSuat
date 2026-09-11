from pydantic import BaseModel
from PIL.Image import Image
from .LlmService import LlmAgent, pil_to_base64, Message

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
            Message(
                role="system",
                content="You are an AI agent that generates a bounding box for an image ordered. Clip the bounding box for the ordered area and return the coordinates in the format: {x, y, width, height}. The coordinates should be integers. Make sure the bounding box is tight and does not include any extra area but covers all the specified content."
            ),
            Message(
                role="tool",
                content=image_data
            ),
            Message(
                role="user",
                content=f"Order: {order}"
            )
        ]
        response = self.generate_response_in_format[BoundingBox](messages)
        return response
