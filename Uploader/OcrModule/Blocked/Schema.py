from enum import Enum
from pydantic import BaseModel, Field

class BlockType(str, Enum):
    TEXT = "text"
    MATH = "math"
    IMAGE = "image"
    TABLE = "table"

class Block(BaseModel):
    block_type: BlockType = Field(..., description="The type of the block.")
    page_number: int = Field(..., description="The page number where the block is located.")
    bounding_box: tuple[int, int, int, int] = Field(
        ..., description="The bounding box of the block in (x, y, width, height) format."
    )

class BlockerResult(BaseModel):
    blocks: list[Block] = Field(..., description="List of blocks detected in the document.")
