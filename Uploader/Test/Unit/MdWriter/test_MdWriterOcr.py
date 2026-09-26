"""Tests for the whole MdWriter pipeline, with a fake detector and a fake model."""

import re
import threading
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from PIL import Image, ImageDraw
from PIL.Image import Image as PilImage

from OcrModule.MdWriter.FigureDetector import FigureDetector
from OcrModule.MdWriter.MdWriterOcr import MdWriterOcr
from OcrModule.MdWriter.ReferenceReader import ReferenceReader
from OcrModule.MdWriter.Transcriber.PageTranscriber import PageTranscriber
from OcrModule.OcrSchema import OcrResultBlockFigure, OcrResultBlockTableOfContents


class OneFigurePerOddPage(FigureDetector):
    """Finds one figure on every page whose width is odd."""

    def _detect_page_figures(self, page: PilImage) -> list[tuple[int, int, int, int]]:
        return [(0, 0, 5, 5)] if page.width % 2 else []


class PageEchoModel(BaseChatModel):
    """Writes the page it is asked for as "page N", placing its figures.

    Every page says both of its ends run over the page turn, so every turn is
    joined and the joins between pages are exercised."""

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
        match = re.match(
            r"Page (\d+) of \d+ \((?:figures ([\d, ]+)|no figures)\)", label
        )
        assert match is not None
        page, ids = int(match.group(1)) - 1, match.group(2)

        markdown = f"page {page}" + "".join(
            f"\n\n![fig {i}](figure:{i})" for i in (ids.split(", ") if ids else [])
        )
        markdown = f"<!--continues-previous-->{markdown}<!--continued-by-next-->"

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
    return [
        printed(Image.new("RGB", (40 + index, 40), "white")) for index in range(count)
    ]


def printed(page: PilImage) -> PilImage:
    """The page with a block of print away from the figure box, so it is not blank."""
    ImageDraw.Draw(page).rectangle((20, 20, 30, 30), fill="black")
    return page


def build() -> tuple[MdWriterOcr, PageEchoModel]:
    model = PageEchoModel(requests=[], lock=threading.Lock())
    ocr = MdWriterOcr(OneFigurePerOddPage(), PageTranscriber(model))
    return ocr, model


def test_every_page_is_written_once_and_the_pages_are_joined():
    ocr, model = build()

    draft = ocr.write_markdown(pages(3))

    assert len(model.requests) == 3
    assert draft.markdown == (
        "<!--page:0-->page 0 <!--page:1-->page 1 <!--page:2-->page 2"
        "\n\n![fig 0](figure:0)"
    )


def test_the_document_tree_is_built_from_the_markdown():
    ocr, _ = build()

    root = ocr.ocr(pages(2)).root_section

    blocks = root.section_content
    assert [
        (b.block_type, b.existing_pages, getattr(b, "text", None)) for b in blocks
    ] == [
        ("paragraph", [0, 1], "page 0 page 1"),
        ("figure", [1], None),
    ]
    assert isinstance(blocks[1], OcrResultBlockFigure)
    assert blocks[1].caption == "fig 0"
    assert root.existing_pages == [0, 1]


def test_the_rendered_pages_carry_the_figure_boxes():
    ocr, _ = build()

    draft = ocr.write_markdown(pages(2))

    assert draft.rendered_pages[1].getpixel((0, 4)) != (255, 255, 255)
    assert draft.rendered_pages[0].getpixel((0, 4)) == (255, 255, 255)


def test_a_single_page_ignores_its_continuation_markers():
    ocr, model = build()

    draft = ocr.write_markdown(pages(1))

    assert len(model.requests) == 1
    assert draft.markdown == "<!--page:0-->page 0"


class NumberingReader(ReferenceReader):
    """Reads every page as the width it was drawn at."""

    def _read_page(self, page: PilImage) -> str:
        return f"width {page.width}"


def test_every_page_is_sent_its_own_reference():
    model = PageEchoModel(requests=[], lock=threading.Lock())
    ocr = MdWriterOcr(
        OneFigurePerOddPage(),
        PageTranscriber(model),
        reference_reader=NumberingReader(),
    )

    ocr.write_markdown(pages(2))

    references = sorted(texts(request)[-1] for request in model.requests)
    assert references == [
        "<reference_ocr>\nwidth 40\n</reference_ocr>",
        "<reference_ocr>\nwidth 41\n</reference_ocr>",
    ]


class NoFigures(FigureDetector):
    """Finds no figure on any page."""

    def _detect_page_figures(self, page: PilImage) -> list[tuple[int, int, int, int]]:
        return []


class TableOfContentsModel(PageEchoModel):
    """Writes every page as one chapter of a table of contents and its section,
    marking both ends as running over the page turn all the same."""

    def _generate(
        self, messages: list[BaseMessage], *args: Any, **kwargs: Any
    ) -> ChatResult:
        label = next(text for text in texts(messages) if text.startswith("Page "))
        chapter = label.split()[1]
        markdown = (
            "<!--continues-previous-->:::toc\n"
            f"- {chapter} | Chapter {chapter} | {chapter}0\n"
            f"  - {chapter}.1 | Section {chapter}.1 | {chapter}1\n"
            ":::<!--continued-by-next-->"
        )
        return ChatResult(generations=[ChatGeneration(message=AIMessage(markdown))])


def test_a_table_of_contents_over_the_pages_is_one_block():
    model = TableOfContentsModel(requests=[], lock=threading.Lock())
    ocr = MdWriterOcr(NoFigures(), PageTranscriber(model))

    blocks = ocr.ocr(pages(2)).root_section.section_content

    assert [b.block_type for b in blocks] == ["table_of_contents"]
    toc = blocks[0]
    assert isinstance(toc, OcrResultBlockTableOfContents)
    assert toc.existing_pages == [0, 1]
    assert [(e.section_number, e.title, e.page_number) for e in toc.entries] == [
        ("1", "Chapter 1", "10"),
        ("2", "Chapter 2", "20"),
    ]
    assert [e.title for e in toc.entries[1].children] == ["Section 2.1"]
