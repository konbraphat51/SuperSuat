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
    role: Literal["system", "user", "assistant"]
    content: str


class LlmAgent:
    def __init__(
        self,
        client: OpenAI,
        model: str
    ) -> None:
        self.client = client
        self.model = model

    def generate_response_in_format[Format](
        self,
        messages: list[Message]
    ) -> Format:
        completion = self.client.responses.parse(
            model=self.model,
            input=self._convert_messages(messages),
            response_format=Format
        )
        return completion

    def _convert_messages(
        self,
        messages: list[Message],
    ) -> list[dict[str, str]]:
        return [
            {
                "role": message.role,
                "content": message.content,
            }
            for message in messages
        ]
