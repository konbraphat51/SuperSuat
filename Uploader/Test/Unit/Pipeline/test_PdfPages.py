"""Tests for rendering the pages of a PDF lazily."""

from pathlib import Path

import fitz  # PyMuPDF
import pytest

from Pipeline.PdfPages import LazyPdfPages


@pytest.fixture
def pdf_path(tmp_path: Path) -> Path:
    """A PDF of three pages, each an inch across and two inches tall."""
    path = tmp_path / "three.pdf"
    with fitz.open() as document:
        for _ in range(3):
            document.new_page(width=72, height=144)
        document.save(path)
    return path


def test_every_page_is_rendered_at_the_dpi(pdf_path: Path):
    with LazyPdfPages(pdf_path, dpi=100) as pages:
        assert len(pages) == 3
        assert pages[0].size == (100, 200)
        assert pages[-1].mode == "RGB"


def test_max_pages_holds_only_the_first_pages(pdf_path: Path):
    with LazyPdfPages(pdf_path, dpi=72, max_pages=2) as pages:
        assert len(pages) == 2
        assert len(list(pages)) == 2
        with pytest.raises(IndexError):
            pages[2]


def test_a_slice_renders_the_pages_it_covers(pdf_path: Path):
    with LazyPdfPages(pdf_path, dpi=72) as pages:
        assert len(pages[1:]) == 2
