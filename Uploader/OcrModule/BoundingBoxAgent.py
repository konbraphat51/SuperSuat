from pydantic import BaseModel
from PIL.Image import Image
from openai import OpenAI
from .LlmService import pil_to_base64, Message, convert_messages

class BoundingBox(BaseModel):
    x: int
    y: int
    width: int
    height: int

class BoundingBoxAgent:
    def __init__(
        self,
        client: OpenAI,
        model: str
    ) -> None:
        self.client = client
        self.model = model

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
        response = self.client.chat.completions.create(
            model=self.model,
            messages=convert_messages(messages),
            response_format=BoundingBox
        )
        return response
