"""Tests for the document's figures being held, drawn and corrected."""

from PIL import Image

from OcrModule.MdWriter.FigureBoard import FigureBoard
from OcrModule.MdWriter.Schema import CorrectedFigure, DetectedFigure

PAGES = [Image.new("RGB", (100, 100), "white") for _ in range(2)]


def board() -> FigureBoard:
    return FigureBoard(
        PAGES,
        [
            DetectedFigure(block_id=0, page_index=0, bounding_box=(10, 10, 20, 20)),
            DetectedFigure(block_id=1, page_index=0, bounding_box=(10, 50, 20, 20)),
            DetectedFigure(block_id=2, page_index=1, bounding_box=(0, 0, 50, 50)),
        ],
    )


def test_figures_are_told_apart_by_page():
    figures = board()

    assert figures.figure_ids_on(0) == [0, 1]
    assert figures.figure_ids_on(1) == [2]
    assert [figure.block_id for figure in figures.figures] == [0, 1, 2]


def test_a_page_is_drawn_with_its_figures_and_left_as_scanned():
    figures = board()

    rendered = figures.rendered(0)

    assert rendered.getpixel((10, 65)) != (255, 255, 255)
    assert figures.page(0).getpixel((10, 65)) == (255, 255, 255)


def test_a_correction_keeps_the_ids_it_names_and_numbers_new_figures_past_all():
    figures = board()

    corrected = figures.replace(
        0,
        [
            CorrectedFigure(block_id=None, bounding_box=(60, 60, 30, 30)),
            CorrectedFigure(block_id=0, bounding_box=(5, 5, 40, 40)),
        ],
    )

    assert [(f.block_id, f.bounding_box) for f in corrected] == [
        (0, (5, 5, 40, 40)),
        (3, (60, 60, 30, 30)),
    ]
    assert figures.figure_ids_on(0) == [0, 3]
    assert [figure.block_id for figure in figures.figures] == [0, 3, 2]


def test_an_id_of_another_page_or_named_twice_is_given_a_new_one():
    figures = board()

    corrected = figures.replace(
        0,
        [
            CorrectedFigure(block_id=2, bounding_box=(0, 0, 10, 10)),
            CorrectedFigure(block_id=1, bounding_box=(0, 20, 10, 10)),
            CorrectedFigure(block_id=1, bounding_box=(0, 40, 10, 10)),
        ],
    )

    assert [figure.block_id for figure in corrected] == [3, 1, 4]
    assert figures.figure_ids_on(1) == [2]


def test_a_corrected_page_is_drawn_again():
    figures = board()
    before = figures.rendered(0)

    figures.replace(0, [])

    assert figures.rendered(0) is not before
    assert figures.rendered(0).getpixel((10, 65)) == (255, 255, 255)
