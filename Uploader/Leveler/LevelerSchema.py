"""The heading levels the leveler model answers with."""

from pydantic import BaseModel, Field


class HeadingLevel(BaseModel):
    """The level one heading holds in the document's hierarchy.

    Attributes:
        target_block_id: The heading block this level is for.
        heading_level: The level itself, 1 for the document's own title.
    """

    target_block_id: int = Field(
        description="The block_id of the heading block to set the level for."
    )
    heading_level: int = Field(
        description="The level of this heading in the document's hierarchy. The document's own title is 1, a chapter under it is 2, a section under that is 3, and so on."
    )


class HeadingLevels(BaseModel):
    """One level per heading of the document.

    Attributes:
        levels: The level of each heading, one entry per heading.
    """

    levels: list[HeadingLevel] = Field(
        description="The level of every heading you were given, one entry per heading, in any order."
    )
