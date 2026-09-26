"""A leveler model answering from a script, and the document trees the leveler tests build."""

from typing import Any

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.runnables import RunnableLambda
from PIL import Image

from Leveler.LevelerSchema import SkeletonLevels
from OcrModule.OcrSchema import OcrResultBlock, OcrResultBlockText, OcrResultSection

# A scripted answer: each heading's level, or its level and whether it needs its page.
Reply = dict[int, float | tuple[float, bool]]


class ScriptedLevelModel(GenericFakeChatModel):
    """Answers each structured request with the next scripted levels, keeping
    every request it got and the answer type it was asked for."""

    replies: list[Reply] = []
    requests: list[list[BaseMessage]] = []
    answer_types: list[str] = []

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
        def answer(messages: list[BaseMessage]) -> Any:
            # a copy: the caller keeps appending to the same list between attempts
            self.requests.append(list(messages))
            self.answer_types.append(schema.__name__)
            return schema.model_validate(
                {
                    "levels": [
                        _entry(schema, *item) for item in self.replies.pop(0).items()
                    ]
                }
            )

        return RunnableLambda(answer)


def _entry(schema: Any, block_id: int, reply: float | tuple[float, bool]) -> dict:
    level, needs_page = reply if isinstance(reply, tuple) else (reply, False)
    entry: dict[str, Any] = {"target_block_id": block_id, "heading_level": level}
    if schema is SkeletonLevels:
        entry["needs_page_image"] = needs_page
    return entry


def scripted(*replies: Reply) -> ScriptedLevelModel:
    return ScriptedLevelModel(
        messages=iter([]), replies=list(replies), requests=[], answer_types=[]
    )


def text(block_index: int, block_type: str = "paragraph", page: int = 0):
    return OcrResultBlockText(
        block_type=block_type,  # type: ignore[arg-type]
        existing_pages=[page],
        block_index=block_index,
        text=f"text {block_index}",
    )


def section(block_index: int, *content: OcrResultBlock) -> OcrResultSection:
    return OcrResultSection(
        block_type="section",
        existing_pages=[],
        block_index=block_index,
        section_content=list(content),
    )


def shape(tree: OcrResultSection) -> list:
    """The tree as nested lists of the block indices of its non-section blocks."""
    return [
        shape(block) if isinstance(block, OcrResultSection) else block.block_index
        for block in tree.section_content
    ]


def pages(count: int) -> list[Image.Image]:
    return [Image.new("RGB", (10, 10), "white") for _ in range(count)]


def request_text(messages: list[BaseMessage]) -> str:
    """Every text of the request's human message, joined."""
    human = next(m for m in messages if isinstance(m, HumanMessage))
    if isinstance(human.content, str):
        return human.content
    return "\n".join(
        part["text"]
        for part in human.content
        if isinstance(part, dict) and part.get("type") == "text"
    )


def image_count(messages: list[BaseMessage]) -> int:
    """How many images the request's human message carries."""
    human = next(m for m in messages if isinstance(m, HumanMessage))
    if isinstance(human.content, str):
        return 0
    return sum(
        1
        for part in human.content
        if isinstance(part, dict) and part.get("type") in ("image", "image_url")
    )
