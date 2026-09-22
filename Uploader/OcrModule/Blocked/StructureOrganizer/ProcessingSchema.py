# Schemas for blocks as they move through the structure-organizing stage.

from dataclasses import dataclass
from typing import Literal
from ..Schema import (
    BlockType,
    BlockerResult,
    Block,
    TranscriptionResult,
    TranscriptionBlock,
)
from ...OcrSchema import TEXT_BLOCK_TYPES


@dataclass(kw_only=True)
class ProcessingBlock:
    """A block being organized into the document's final structure.

    Attributes:
        block_id: The unique identifier of the block, matching Block.block_id.
        page_number: The 0-indexed page the block was found on.
        recognized_blocker_type: The block type as detected by the Blocker.
        new_type: The type assigned by the organizer, if labeled.
        have_been_labeled: Whether new_type has been assigned.
        have_been_checked: Whether this block has been reviewed.
    """

    block_id: int
    page_number: int
    recognized_blocker_type: BlockType
    new_type: TEXT_BLOCK_TYPES | Literal["figure", "section"] | None = None
    have_been_labeled: bool = False
    have_been_checked: bool = False


@dataclass(kw_only=True)
class ProcessingBlockText(ProcessingBlock):
    """A ProcessingBlock holding transcribed text.

    Attributes:
        text: The transcribed text of the block.
        have_been_edited: Whether text has been manually edited.
    """

    text: str
    have_been_edited: bool = False


@dataclass(kw_only=True)
class ProcessingBlockTextHeading(ProcessingBlockText):
    """A ProcessingBlockText representing a heading.

    Attributes:
        heading_level: The heading's level, if determined.
    """

    heading_level: int | None = None


@dataclass(kw_only=True)
class ProcessingBlockFigure(ProcessingBlock):
    """A ProcessingBlock representing a figure/image.

    Attributes:
        bounding_box: The bounding box of the block in (x, y, width, height) format.
        have_caption_set: Whether a caption has been assigned to this figure.
        caption_text_block_id: The block_id of the caption text block, if set.
    """

    bounding_box: tuple[int, int, int, int]
    have_caption_set: bool = False
    caption_text_block_id: int | None = None


def convert_blocker_result_to_processing_blocks(
    blocker_result: BlockerResult,
    transcription_result: TranscriptionResult | None = None,
) -> list[ProcessingBlock]:
    """Converts a BlockerResult into ProcessingBlocks for structure organizing.

    Fields with no corresponding data in BlockerResult and transcription_result
    are left at their dataclass defaults.

    Args:
        blocker_result: The blocks detected by a Blocker.
        transcription_result: The transcribed text of the blocks, if available.
    """
    texts_by_block_id: dict[int, str] = (
        {t.block_id: t.text for t in transcription_result.transcriptions}
        if transcription_result is not None
        else {}
    )

    processing_blocks: list[ProcessingBlock] = []

    for block in blocker_result.blocks:
        if block.block_type == BlockType.IMAGE:
            processing_blocks.append(
                ProcessingBlockFigure(
                    block_id=block.block_id,
                    page_number=block.page_number,
                    recognized_blocker_type=block.block_type,
                    bounding_box=block.bounding_box,
                )
            )
        else:
            # TEXT, MATH, and TABLE are handled as text blocks; fill text
            # from transcription_result if available, otherwise leave empty.
            processing_blocks.append(
                ProcessingBlockText(
                    block_id=block.block_id,
                    page_number=block.page_number,
                    recognized_blocker_type=block.block_type,
                    text=texts_by_block_id.get(block.block_id, ""),
                )
            )

    return processing_blocks
