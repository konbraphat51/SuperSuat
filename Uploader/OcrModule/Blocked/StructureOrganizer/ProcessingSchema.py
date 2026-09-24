# Schemas for blocks as they move through the structure-organizing stage.

from dataclasses import dataclass, fields
from typing import Literal, TypeVar

from ...OcrSchema import TEXT_BLOCK_TYPES
from ..Schema import (
    BlockerResult,
    TranscriptionResult,
    TranscriptionTarget,
    TranscriptionType,
)

BLOCK_LABELS = TEXT_BLOCK_TYPES | Literal["figure"]
"""What a block can be labeled: any text block type, or a figure."""

# The label whose text is read as a table rather than as running text.
TABLE_LABEL = "table"

# The label of a block that holds no text at all.
FIGURE_LABEL = "figure"

# The label of a block that opens a section of the document.
HEADING_LABEL = "heading"


@dataclass(kw_only=True)
class ProcessingBlock:
    """A block being organized into the document's final structure.

    A block starts out as this, knowing only where it is, and becomes a text
    block or a figure once the Classifier says which it is.

    Attributes:
        block_id: The unique identifier of the block, matching Block.block_id.
        page_index: The page the block was found on, 0-indexed.
        bounding_box: The bounding box of the block in (x, y, width, height) format.
        new_type: The type assigned by the organizer, if labeled.
        have_been_labeled: Whether new_type has been assigned.
        have_been_checked: Whether this block has been reviewed.
    """

    block_id: int
    page_index: int
    bounding_box: tuple[int, int, int, int]
    new_type: BLOCK_LABELS | None = None
    have_been_labeled: bool = False
    have_been_checked: bool = False


@dataclass(kw_only=True)
class ProcessingBlockText(ProcessingBlock):
    """A ProcessingBlock holding text, which the Transcriber reads later.

    Attributes:
        text: The transcribed text of the block, empty until it is read.
        merging_previous_page: Whether this block is the rest of a block the
            previous page broke off, to be written down as one block.
    """

    text: str = ""
    merging_previous_page: bool = False


@dataclass(kw_only=True)
class ProcessingBlockTextHeading(ProcessingBlockText):
    """A ProcessingBlockText representing a heading.

    Attributes:
        heading_level: The heading's level, if determined.
    """

    heading_level: int | None = None


@dataclass(kw_only=True)
class ProcessingBlockFigure(ProcessingBlock):
    """A ProcessingBlock representing a figure, which holds no text of its own.

    Attributes:
        have_caption_checked: Whether a caption has been checked for this figure.
        caption_text_block_id: The block_id of the caption text block, if set.
    """

    have_caption_checked: bool = False
    caption_text_block_id: int | None = None


AnyProcessingBlock = TypeVar("AnyProcessingBlock", bound=ProcessingBlock)


def convert_blocker_result_to_processing_blocks(
    blocker_result: BlockerResult,
) -> list[ProcessingBlock]:
    """The Blocker's blocks as unlabeled ProcessingBlocks, in the order given.

    Nothing is assumed about what a block holds: the Classifier labels each
    one, and labeling is what turns it into a text block or a figure.

    Args:
        blocker_result: The blocks detected by a Blocker.
    """
    return [
        ProcessingBlock(
            block_id=block.block_id,
            page_index=block.page_index,
            bounding_box=block.bounding_box,
        )
        for block in blocker_result.blocks
    ]


def rebuild_block_as(
    block: ProcessingBlock,
    block_kind: type[AnyProcessingBlock],
) -> AnyProcessingBlock:
    """The block as `block_kind`, keeping every field the two kinds share.

    A block changes kind whenever it is labeled: a paragraph called a heading
    gains a level, and a heading called a paragraph loses one. Whatever the
    target kind does not hold goes back to its default, which is what keeps a
    block that is no longer a heading from being treated as one.
    """
    if type(block) is block_kind:
        return block

    kept_names = {field.name for field in fields(block_kind)}

    return block_kind(
        **{
            field.name: getattr(block, field.name)
            for field in fields(block)
            if field.name in kept_names
        }
    )


def build_transcription_targets(
    processing_blocks: list[ProcessingBlock],
) -> list[TranscriptionTarget]:
    """What the Transcriber has to read, in reading order.

    A figure holds no text, so it is not read; everything else is, as a table
    or as running text depending on what the Classifier called it.
    """
    return [
        TranscriptionTarget(
            block_id=block.block_id,
            page_index=block.page_index,
            bounding_box=block.bounding_box,
            transcription_type=(
                TranscriptionType.TABLE
                if block.new_type == TABLE_LABEL
                else TranscriptionType.TEXT
            ),
        )
        for block in processing_blocks
        if isinstance(block, ProcessingBlockText)
    ]


def apply_transcriptions(
    processing_blocks: list[ProcessingBlock],
    transcription_result: TranscriptionResult,
) -> None:
    """Writes each transcription onto its block, editing the blocks in place."""
    texts_by_block_id = {
        transcription.block_id: transcription.text
        for transcription in transcription_result.transcriptions
    }

    for block in processing_blocks:
        if isinstance(block, ProcessingBlockText):
            block.text = texts_by_block_id.get(block.block_id, block.text)
