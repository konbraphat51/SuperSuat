"""Tests for the settled blocks being turned into the document tree."""

from OcrModule.Blocked.Schema import TranscriptionBlock, TranscriptionResult
from OcrModule.Blocked.StructureOrganizer.DataExporter import (
    export_processing_blocks_to_ocr_result,
)
from OcrModule.Blocked.StructureOrganizer.ProcessingSchema import (
    ProcessingBlock,
    ProcessingBlockFigure,
    ProcessingBlockText,
    ProcessingBlockTextHeading,
    apply_transcriptions,
    build_transcription_targets,
)
from OcrModule.OcrSchema import OcrResultSection

BOX = (0, 0, 100, 10)


def text(block_id: int, body: str, page_index: int = 0, **kwargs) -> ProcessingBlockText:
    return ProcessingBlockText(
        block_id=block_id,
        page_index=page_index,
        bounding_box=BOX,
        new_type=kwargs.pop("new_type", "paragraph"),
        have_been_labeled=True,
        text=body,
        **kwargs,
    )


def heading(
    block_id: int, body: str, level: int, page_index: int = 0
) -> ProcessingBlockTextHeading:
    return ProcessingBlockTextHeading(
        block_id=block_id,
        page_index=page_index,
        bounding_box=BOX,
        new_type="heading",
        have_been_labeled=True,
        text=body,
        heading_level=level,
    )


def figure(block_id: int, page_index: int = 0, **kwargs) -> ProcessingBlockFigure:
    return ProcessingBlockFigure(
        block_id=block_id,
        page_index=page_index,
        bounding_box=BOX,
        new_type="figure",
        have_been_labeled=True,
        **kwargs,
    )


def flatten(section: OcrResultSection, depth: int = 0) -> list[tuple[int, str]]:
    """(depth, block_type) of every block of the tree, in document order."""
    flattened: list[tuple[int, str]] = []

    for block in section.section_content:
        if isinstance(block, OcrResultSection):
            flattened.append((depth, "section"))
            flattened += flatten(block, depth + 1)
        else:
            flattened.append((depth, block.block_type))

    return flattened


def test_headings_nest_by_their_level():
    blocks: list[ProcessingBlock] = [
        heading(0, "Title", 1),
        heading(1, "Chapter", 2),
        text(2, "body"),
        heading(3, "Section", 3),
        text(4, "deeper"),
        heading(5, "Chapter 2", 2),
        text(6, "sibling"),
    ]

    tree = export_processing_blocks_to_ocr_result(blocks)

    assert flatten(tree.root_section) == [
        (0, "section"),
        (1, "heading"),
        (1, "section"),
        (2, "heading"),
        (2, "paragraph"),
        (2, "section"),
        (3, "heading"),
        (3, "paragraph"),
        (1, "section"),
        (2, "heading"),
        (2, "paragraph"),
    ]


def test_a_heading_without_a_level_opens_no_section():
    unleveled = heading(0, "Title", 1)
    unleveled.heading_level = None

    tree = export_processing_blocks_to_ocr_result([unleveled, text(1, "body")])

    assert flatten(tree.root_section) == [(0, "heading"), (0, "paragraph")]


def test_a_caption_is_folded_into_its_figure():
    blocks: list[ProcessingBlock] = [
        figure(0, caption_text_block_id=1, have_caption_checked=True),
        text(1, "Figure 1. A cat."),
    ]

    tree = export_processing_blocks_to_ocr_result(blocks)

    (figure_block,) = tree.root_section.section_content
    assert figure_block.block_type == "figure"
    assert figure_block.caption == "Figure 1. A cat."


def test_a_block_continuing_the_previous_page_is_joined_into_one():
    blocks: list[ProcessingBlock] = [
        text(0, "The sentence starts here", page_index=0),
        text(1, "and ends here.", page_index=1, merging_previous_page=True),
    ]

    tree = export_processing_blocks_to_ocr_result(blocks)

    (paragraph,) = tree.root_section.section_content
    assert paragraph.text == "The sentence starts here and ends here."
    assert paragraph.existing_pages == [0, 1]


def test_a_japanese_join_takes_no_space():
    blocks: list[ProcessingBlock] = [
        text(0, "文章はここから", page_index=0),
        text(1, "ここまで。", page_index=1, merging_previous_page=True),
    ]

    tree = export_processing_blocks_to_ocr_result(blocks)

    (paragraph,) = tree.root_section.section_content
    assert paragraph.text == "文章はここからここまで。"


def test_a_block_left_unlabeled_is_written_down_as_a_paragraph():
    unlabeled = ProcessingBlockText(block_id=0, page_index=0, bounding_box=BOX, text="?")

    tree = export_processing_blocks_to_ocr_result([unlabeled])

    (block,) = tree.root_section.section_content
    assert block.block_type == "paragraph"


def test_only_text_blocks_are_read_and_a_table_is_read_as_one():
    blocks: list[ProcessingBlock] = [
        text(0, "", new_type="table"),
        text(1, ""),
        figure(2),
    ]

    targets = build_transcription_targets(blocks)

    assert [(target.block_id, target.transcription_type.value) for target in targets] == [
        (0, "table"),
        (1, "text"),
    ]


def test_transcriptions_are_written_onto_their_blocks():
    blocks: list[ProcessingBlock] = [text(0, ""), figure(1)]

    apply_transcriptions(
        blocks,
        TranscriptionResult([TranscriptionBlock(block_id=0, text="read text")]),
    )

    assert blocks[0].text == "read text"
