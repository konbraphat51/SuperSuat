import base64
import io
from typing import Literal
from dataclasses import dataclass
from PIL.Image import Image
from langchain_protocol import Literal
from openai import OpenAI

def pil_to_base64(image: Image) -> str:
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

@dataclass
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: str | Image

def convert_messages(
    self,
    messages: list[Message],
) -> list[dict[str, str]]:
    results = []

    for message in messages:
        if isinstance(message.content, Image):
            content = {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{pil_to_base64(message.content)}",
                    "detail": "auto"
                }
            }
        else:
            content = message.content

        results.append({
            "role": message.role,
            "content": content
        })

    return results
