"""What the stages of the blocked pipeline hand each other."""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class BoxedBlock(Protocol):
    """Anything that is a box on a page with an id, whatever else it holds.

    A block keeps its id and its box through the whole pipeline, while what is
    known about it grows; this is what the parts that only need those two -
    drawing a block, cropping it - ask for.

    Attributes:
        block_id: The unique identifier of the block within the document.
        bounding_box: The bounding box of the block in (x, y, width, height) format.
    """

    block_id: int
    bounding_box: tuple[int, int, int, int]


@dataclass
class Block:
    """One region of a page, as the Blocker found it.

    The Blocker only says where a block is; what it is is settled later, by
    the Classifier reading the page.

    Attributes:
        page_index: The page the block is on, 0-indexed.
        bounding_box: The bounding box of the block in (x, y, width, height) format.
        block_id: A unique identifier for the block within the document.
    """

    page_index: int
    bounding_box: tuple[int, int, int, int]
    block_id: int


@dataclass
class BlockerResult:
    """The result of running a blocker over a document.

    Attributes:
        blocks: List of blocks detected in the document.
    """

    blocks: list[Block]


class TranscriptionType(str, Enum):
    """How a block's image is to be read.

    A table needs its own reading, into a Markdown table; everything else
    reads as text, whatever kind of text it turned out to be.
    """

    TEXT = "text"
    TABLE = "table"


@dataclass
class TranscriptionTarget:
    """One block to read, and how to read it.

    Attributes:
        block_id: The unique identifier of the block.
        page_index: The page the block is on, 0-indexed.
        bounding_box: The bounding box of the block in (x, y, width, height) format.
        transcription_type: How the block's image is to be read.
    """

    block_id: int
    page_index: int
    bounding_box: tuple[int, int, int, int]
    transcription_type: TranscriptionType


@dataclass
class TranscriptionBlock:
    """A transcribed block of text.

    Attributes:
        block_id: The unique identifier of the block.
        text: The transcribed text of the block.
    """

    block_id: int
    text: str


@dataclass
class TranscriptionResult:
    """The result of transcribing a document's blocks.

    Attributes:
        transcriptions: List of transcribed blocks.
    """

    transcriptions: list[TranscriptionBlock]
