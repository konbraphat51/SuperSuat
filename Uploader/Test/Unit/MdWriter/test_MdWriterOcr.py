"""Tests for the whole MdWriter pipeline, with a fake detector and a fake model."""

import re
import threading
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from PIL import Image
from PIL.Image import Image as PilImage

from OcrModule.MdWriter.FigureDetector import FigureDetector
from OcrModule.MdWriter.MdWriterOcr import MdWriterOcr
from OcrModule.MdWriter.Transcriber.PageTranscriber import PageTranscriber
from OcrModule.MdWriter.Transcriber.prompt import FILL_PROMPT
from OcrModule.OcrSchema import OcrResultBlockFigure, OcrResultBlockText


class OneFigurePerOddPage(FigureDetector):
    """Finds one figure on every page whose width is odd."""

    def _detect_page_figures(self, page: PilImage) -> list[tuple[int, int, int, int]]:
        return [(0, 0, 5, 5)] if page.width % 2 else []


class PageEchoModel(BaseChatModel):
    """Writes the page it is asked for as "page N", placing its figures.

    A fill page always continues the paragraph before it, so the joins
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

        label = next(text for text in texts(messages) if text.startswith("Page "))
        match = re.match(r"Page (\d+) \((?:figures ([\d, ]+)|no figures)\)", label)
        assert match is not None
        page, ids = int(match.group(1)), match.group(2)

        markdown = f"page {page}" + "".join(
            f"\n\n![fig {i}](figure:{i})" for i in (ids.split(", ") if ids else [])
        )
        if messages[0].content == FILL_PROMPT:
            markdown = f"<!--continues-previous-->{markdown}"

        return ChatResult(generations=[ChatGeneration(message=AIMessage(markdown))])


def texts(messages: list[BaseMessage]) -> list[str]:
    """The text blocks of a request's human message."""
    return [
        block["text"]
        for block in messages[1].content
        if isinstance(block, dict) and block.get("type") == "text"
    ]


def pages(count: int) -> list[PilImage]:
    # the width says which page it is, and odd pages hold a figure
    return [Image.new("RGB", (40 + index, 40), "white") for index in range(count)]


def build() -> tuple[MdWriterOcr, PageEchoModel]:
    model = PageEchoModel(requests=[], lock=threading.Lock())
    ocr = MdWriterOcr(OneFigurePerOddPage(), PageTranscriber(model))
    return ocr, model


def test_every_page_is_written_once_and_the_parts_are_joined():
    ocr, model = build()

    draft = ocr.write_markdown(pages(5))

    assert len(model.requests) == 5
    assert draft.markdown == (
        "<!--page:0-->page 0 "
        "<!--page:1-->page 1\n\n![fig 0](figure:0)\n\n"
        "<!--page:2-->page 2 "
        "<!--page:3-->page 3\n\n![fig 1](figure:1)\n\n"
        "<!--page:4-->page 4"
    )


def test_a_fill_page_is_sent_the_markdown_of_both_neighbours():
    ocr, model = build()

    ocr.write_markdown(pages(3))

    fill = next(r for r in model.requests if r[0].content == FILL_PROMPT)
    sent = texts(fill)
    assert sent[0] == "<previous_page>\npage 0\n</previous_page>"
    assert sent[-1] == "<next_page>\npage 2\n</next_page>"


def test_the_document_tree_is_built_from_the_markdown():
    ocr, _ = build()

    root = ocr.ocr(pages(4)).root_section

    blocks = root.section_content
    assert [
        (b.block_type, b.existing_pages, getattr(b, "text", None)) for b in blocks
    ] == [
        ("paragraph", [0, 1], "page 0 page 1"),
        ("figure", [1], None),
        ("paragraph", [2, 3], "page 2 page 3"),
        ("figure", [3], None),
    ]
    assert isinstance(blocks[1], OcrResultBlockFigure)
    assert blocks[1].caption == "fig 0"
    assert isinstance(blocks[2], OcrResultBlockText)
    assert root.existing_pages == [0, 1, 2, 3]


def test_the_rendered_pages_carry_the_figure_boxes():
    ocr, _ = build()

    draft = ocr.write_markdown(pages(2))

    assert draft.rendered_pages[1].getpixel((0, 4)) != (255, 255, 255)
    assert draft.rendered_pages[0].getpixel((0, 4)) == (255, 255, 255)


def test_a_single_page_is_written_without_a_fill_pass():
    ocr, model = build()

    draft = ocr.write_markdown(pages(1))

    assert len(model.requests) == 1
    assert draft.markdown == "<!--page:0-->page 0"
