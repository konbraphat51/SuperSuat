from typing import Any

from PIL.Image import Image

from ..LlmService import pil_to_base64


def image_message(image: Image) -> dict[str, Any]:
    """A user message carrying only an image."""
    return {
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{pil_to_base64(image)}",
                    "detail": "auto",
                },
            }
        ],
    }


def assistant_message(message: Any) -> dict[str, Any]:
    """The answer of the model, as a message to append to the history."""
    result: dict[str, Any] = {
        "role": "assistant",
        "content": message.content,
    }

    if message.tool_calls:
        result["tool_calls"] = [
            {
                "id": tool_call.id,
                "type": "function",
                "function": {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments,
                },
            }
            for tool_call in message.tool_calls
        ]

    return result


def tool_message(tool_call_id: str, content: str) -> dict[str, Any]:
    """The result of one tool call."""
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": content,
    }
