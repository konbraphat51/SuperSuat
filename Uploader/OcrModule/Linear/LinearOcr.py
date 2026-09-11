from dataclasses import dataclass
from typing import Any

from openai import OpenAI
from PIL.Image import Image

from ..BoundingBoxAgent import BoundingBoxAgent
from ..Ocr import Ocr
from ..OcrSchema import OcrResult, OcrResultSection
from .Document import LinearDocument
from .Messages import assistant_message, image_message, tool_message
from .Pages import PageImages
from .Prompt import SYSTEM_PROMPT, read_page_prompt
from .ToolRunner import ToolRunner
from .Tools import OCR_TOOLS


class LinearOcr(Ocr):
    @dataclass
    class AgentMemory:
        header_page: list[int]

    def __init__(
        self,
        ocr_client: OpenAI,
        ocr_model: str,
        bounding_box_client: OpenAI,
        bounding_box_model: str,
        max_turns: int = 30,
    ) -> None:
        self.ocr_client = ocr_client
        self.ocr_model = ocr_model
        self.bounding_box_agent = BoundingBoxAgent(
            bounding_box_client, bounding_box_model
        )
        self.max_turns = max_turns

        self.agent_memory = self.AgentMemory(
            header_page=[]
        )
        self.document = LinearDocument()
        self.pages = PageImages([])
        self.tool_runner = ToolRunner(
            self.document, self.pages, self.bounding_box_agent
        )

    @property
    def entire_section(self) -> OcrResultSection:
        return self.document.root

    def to_xml(self) -> str:
        """XML representation of the document recognized so far."""
        return self.document.to_xml()

    def ocr(
        self,
        image_data: list[Image],
    ) -> OcrResult:
        self.pages.load(image_data)

        for page in range(len(self.pages)):
            self.read_page(page)

        return OcrResult(blocks=self.document.all_blocks())

    def read_page(
        self,
        current_page: int,
    ) -> OcrResultSection:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": read_page_prompt(
                    current_page, len(self.pages), self.document.to_xml()
                ),
            },
            image_message(self.pages.get(current_page)),
        ]

        for _ in range(self.max_turns):
            response = self.ocr_client.chat.completions.create(
                model=self.ocr_model,
                messages=messages,
                tools=OCR_TOOLS,
            )
            message = response.choices[0].message
            messages.append(assistant_message(message))

            if not message.tool_calls:
                break

            for tool_call in message.tool_calls:
                result, follow_ups = self.tool_runner.call(
                    tool_call.function.name, tool_call.function.arguments
                )
                messages.append(tool_message(tool_call.id, result))
                messages.extend(follow_ups)

        return self.document.root
