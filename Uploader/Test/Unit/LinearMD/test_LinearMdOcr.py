"""Tests for the whole LinearMD pipeline, with a fake detector and a fake model."""

import re
import threading
from typing import Any

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from PIL import Image
from PIL.Image import Image as PilImage

from OcrModule.LinearMD.FigureDetector import FigureDetector
from OcrModule.LinearMD.LinearMdOcr import LinearMdOcr
from OcrModule.LinearMD.Transcriber.BatchTranscriber import BatchTranscriber
from OcrModule.LinearMD.Transcriber.prompt import FILL_PROMPT
from OcrModule.OcrSchema import OcrResultBlockFigure, OcrResultBlockText


class OneFigurePerOddPage(FigureDetector):
    """Finds one figure on every page whose width is odd."""

    def _detect_page_figures(self, page: PilImage) -> list[tuple[int, int, int, int]]:
        return [(0, 0, 5, 5)] if page.width % 2 else []


class PageEchoModel(BaseChatModel):
    """Writes each page it is asked for as "page N", placing its figures.

    A fill batch always continues the paragraph before it, so the joins
    between parts are exercised."""

    requests: list[list[BaseMessage]] = []
    lock: Any = None

    @property
    def _llm_type(self) -> str:
        return "page-echo"

    def _generate(
        self, messages: list[BaseMessage], *args: Any, **kwargs: Any
    ) -> ChatResult:
        with self.lock:
            self.requests.append(list(messages))

        texts = [
            block["text"]
            for block in messages[1].content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        pages = [int(p) for p in re.findall(r"page:(\d+)", texts[-1])]
        figures = {
            int(page): [int(i) for i in ids.split(", ")]
            for page, ids in (
                re.match(r"Page (\d+) \(figures ([\d, ]+)\)", text).groups()  # type: ignore[union-attr]
                for text in texts
                if re.match(r"Page \d+ \(figures", text)
            )
        }

        parts = [
            f"<!--page:{page}-->page {page}"
            + "".join(f"\n\n![fig {i}](figure:{i})" for i in figures.get(page, []))
            for page in pages
        ]
        markdown = "\n\n".join(parts)
        if messages[0].content == FILL_PROMPT:
            markdown = f"<!--continues-previous-->{markdown}"

        return ChatResult(generations=[ChatGeneration(message=AIMessage(markdown))])


def pages(count: int) -> list[PilImage]:
    # the width says which page it is, and odd pages hold a figure
    return [Image.new("RGB", (40 + index, 40), "white") for index in range(count)]


def build(batch_size: int) -> tuple[LinearMdOcr, PageEchoModel]:
    model = PageEchoModel(requests=[], lock=threading.Lock())
    ocr = LinearMdOcr(OneFigurePerOddPage(), BatchTranscriber(model), batch_size)
    return ocr, model


def test_every_page_is_written_once_and_the_parts_are_joined():
    ocr, model = build(batch_size=2)

    draft = ocr.write_markdown(pages(6))

    # batches: write [0,2], fill [2,4] writing 3, write [4,5]
    assert len(model.requests) == 3
    assert draft.markdown == (
        "<!--page:0-->page 0\n\n"
        "<!--page:1-->page 1\n\n![fig 0](figure:0)\n\n"
        "<!--page:2-->page 2 <!--page:3-->page 3\n\n![fig 1](figure:1)\n\n"
        "<!--page:4-->page 4\n\n"
        "<!--page:5-->page 5\n\n![fig 2](figure:2)"
    )


def test_the_document_tree_is_built_from_the_markdown():
    ocr, _ = build(batch_size=2)

    root = ocr.ocr(pages(4)).root_section

    blocks = root.section_content
    assert [
        (b.block_type, b.existing_pages, getattr(b, "text", None)) for b in blocks
    ] == [
        ("paragraph", [0], "page 0"),
        ("paragraph", [1], "page 1"),
        ("figure", [1], None),
        ("paragraph", [2, 3], "page 2 page 3"),
        ("figure", [3], None),
    ]
    assert isinstance(blocks[2], OcrResultBlockFigure)
    assert blocks[2].caption == "fig 0"
    assert isinstance(blocks[3], OcrResultBlockText)
    assert root.existing_pages == [0, 1, 2, 3]


def test_the_rendered_pages_carry_the_figure_boxes():
    ocr, _ = build(batch_size=3)

    draft = ocr.write_markdown(pages(2))

    assert draft.rendered_pages[1].getpixel((0, 4)) != (255, 255, 255)
    assert draft.rendered_pages[0].getpixel((0, 4)) == (255, 255, 255)


def test_a_batch_size_below_two_fails_before_any_page_is_read():
    ocr, model = build(batch_size=1)

    with pytest.raises(ValueError):
        ocr.ocr(pages(3))

    assert model.requests == []
