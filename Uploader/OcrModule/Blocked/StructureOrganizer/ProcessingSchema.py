from dataclasses import dataclass
from typing import Literal
from ..Schema import BlockType
from ...OcrSchema import TEXT_BLOCK_TYPES

@dataclass
class ProcessingBlock:
    block_id: int
    recognized_blocker_type: BlockType
    new_type: TEXT_BLOCK_TYPES | Literal["figure", "section"] | None = None
    have_been_labeled: bool = False
    have_been_checked: bool = False

@dataclass
class ProcessingBlockText(ProcessingBlock):
    text: str
    have_been_edited: bool = False

@dataclass
class ProcessingBlockTextHeading(ProcessingBlockText):
    heading_level: int | None = None

@dataclass
class ProcessingBlockFigure(ProcessingBlock):
    bounding_box: tuple[int, int, int, int] # (x, y, width, height)
    have_caption_set: bool = False
    caption_text_block_id: int | None = None
