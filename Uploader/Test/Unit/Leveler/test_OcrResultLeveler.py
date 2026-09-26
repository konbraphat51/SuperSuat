"""Tests for a transcribed document tree being nested by its heading levels."""

from typing import Any

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.runnables import RunnableLambda
from PIL import Image

import Leveler.OcrResultLeveler as module
from Leveler.LevelerSchema import HeadingLevels
from Leveler.OcrResultLeveler import OcrResultLeveler
from OcrModule.OcrSchema import (
    OcrResult,
    OcrResultBlock,
    OcrResultBlockText,
    OcrResultSection,
)


class ScriptedLevelModel(GenericFakeChatModel):
    """Answers each structured request with the next scripted levels, keeping
    every request it got."""

    replies: list[dict[int, int]] = []
    requests: list[list[BaseMessage]] = []

    def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
        def answer(messages: list[BaseMessage]) -> HeadingLevels:
            # a copy: the caller keeps appending to the same list between attempts
            self.requests.append(list(messages))
            levels = self.replies.pop(0)
            return HeadingLevels.model_validate(
                {
                    "levels": [
                        {"target_block_id": block_id, "heading_level": level}
                        for block_id, level in levels.items()
                    ]
                }
            )

        return RunnableLambda(answer)


def scripted(*replies: dict[int, int]) -> ScriptedLevelModel:
    return ScriptedLevelModel(messages=iter([]), replies=list(replies), requests=[])


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
    """Every text part of the request's human message, joined."""
    human = next(m for m in messages if isinstance(m, HumanMessage))
    assert isinstance(human.content, list)
    return "\n".join(
        part["text"]
        for part in human.content
        if isinstance(part, dict) and part.get("type") == "text"
    )


def flat_document() -> OcrResult:
    """A document whose headings all sit one level deep, as MdWriter writes it."""
    return OcrResult(
        root_section=section(
            0,
            section(1, text(2, "heading"), text(3)),
            section(4, text(5, "heading", page=1), text(6, page=1)),
            section(7, text(8, "heading", page=1), text(9, page=1)),
        )
    )


def test_a_flat_document_is_nested_by_the_levels_given():
    model = scripted({2: 1, 5: 2, 8: 3})
    document = flat_document()

    leveled = OcrResultLeveler(model).level_ocr_result(pages(2), document)

    assert shape(leveled.root_section) == [[2, 3, [5, 6, [8, 9]]]]
    assert leveled.root_section.block_index == 0
    # the given tree is left as it was
    assert shape(document.root_section) == [[2, 3], [5, 6], [8, 9]]


def test_the_heading_text_is_sent_to_the_model():
    model = scripted({2: 1, 5: 2, 8: 2})

    OcrResultLeveler(model).level_ocr_result(pages(2), flat_document())

    sent = request_text(model.requests[0])
    assert '"block_id":5,"page_number":2,"text":"text 5"' in sent


def test_a_heading_left_unanswered_is_asked_about_again():
    model = scripted({2: 1, 5: 2}, {8: 2})

    leveled = OcrResultLeveler(model).level_ocr_result(pages(2), flat_document())

    assert len(model.requests) == 2
    assert "These headings still have no level: 8." in str(
        model.requests[1][-1].content
    )
    assert shape(leveled.root_section) == [[2, 3, [5, 6], [8, 9]]]


def test_a_level_above_the_title_is_refused_and_asked_about_again():
    model = scripted({2: 0, 5: 2, 8: 2}, {2: 1})

    leveled = OcrResultLeveler(model).level_ocr_result(pages(2), flat_document())

    assert "nothing sits above it" in str(model.requests[1][-1].content)
    assert shape(leveled.root_section) == [[2, 3, [5, 6], [8, 9]]]


def test_a_heading_never_leveled_stops_the_run():
    model = scripted({2: 1}, {2: 1}, {2: 1})

    with pytest.raises(RuntimeError, match="2 heading"):
        OcrResultLeveler(model).level_ocr_result(pages(2), flat_document())


def test_later_parts_are_shown_the_levels_already_settled(monkeypatch):
    monkeypatch.setattr(module, "MAX_PAGES_PER_REQUEST", 1)
    model = scripted({2: 1}, {5: 2, 8: 2})

    leveled = OcrResultLeveler(model).level_ocr_result(pages(2), flat_document())

    second = request_text(model.requests[1])
    assert "Levels already settled" in second
    assert '"block_id":2,"page_number":1,"text":"text 2","heading_level":1' in second
    assert shape(leveled.root_section) == [[2, 3, [5, 6], [8, 9]]]


def test_a_document_without_headings_asks_nothing_and_stays_flat():
    model = scripted()
    document = OcrResult(root_section=section(0, text(1), text(2)))

    leveled = OcrResultLeveler(model).level_ocr_result(pages(1), document)

    assert model.requests == []
    assert shape(leveled.root_section) == [1, 2]
