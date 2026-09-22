from dataclasses import dataclass
from enum import Enum


class BlockType(str, Enum):
    TEXT = "text"
    MATH = "math"
    IMAGE = "image"
    TABLE = "table"


@dataclass
class Block:
    """A single detected block within a document page.

    Attributes:
        block_type: The type of the block.
        page_number: The page number where the block is located.
        bounding_box: The bounding box of the block in (x, y, width, height) format.
        block_id: A unique identifier for the block within the document.
    """

    block_type: BlockType
    page_number: int
    bounding_box: tuple[int, int, int, int]
    block_id: int


@dataclass
class BlockerResult:
    """The result of running a blocker over a document.

    Attributes:
        blocks: List of blocks detected in the document.
    """

    blocks: list[Block]


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
