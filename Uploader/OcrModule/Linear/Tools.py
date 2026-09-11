from PIL.Image import Image
import base64
from io import BytesIO
from openai import OpenAI
from ..BoundingBoxAgent import BoundingBoxAgent

def get_page(
    image_data: list[Image],
    page_number: int, # 0-indexed
) -> str:
    image = image_data[page_number]

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return f"data:image/png;base64,{base64_image}" 

def delegate_bounding_box(
    bounding_box_agent_client: OpenAI,
    bounding_box_agent_model: str,
    target_page: Image,
    order_prompt: str,
) -> tuple[int, int, int, int]:
    agent = BoundingBoxAgent(bounding_box_agent_client, bounding_box_agent_model)

    bbox = agent.generate_bounding_box(target_page, order_prompt)

    return (bbox.x, bbox.y, bbox.width, bbox.height)
