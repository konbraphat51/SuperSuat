"""The heading levels the leveler model answers with."""

from pydantic import BaseModel, Field


class HeadingLevel(BaseModel):
    """The level one heading holds in the document's hierarchy.

    Attributes:
        target_block_id: The heading block this level is for.
        heading_level: The level itself, 1 for the document's own title only.
    """

    target_block_id: int = Field(
        description="The block_id of the heading block to set the level for."
    )
    heading_level: float = Field(
        description="The level of this heading in the document's hierarchy. Level 1 is the document's own title and nothing else; a chapter under it is 2, a section under that is 3, and so on. A heading that ranks between two levels already settled takes a decimal between them, such as 2.5."
    )


class HeadingLevels(BaseModel):
    """One level per heading asked about.

    Attributes:
        levels: The level of each heading, one entry per heading.
    """

    levels: list[HeadingLevel] = Field(
        description="The level of every heading you were asked about, one entry per heading, in any order."
    )


class SkeletonLevel(HeadingLevel):
    """A heading's level judged from text alone, and whether its page is needed.

    Attributes:
        needs_page_image: The text did not settle the level; how the heading is
            printed has to decide it.
    """

    needs_page_image: bool = Field(
        description="True only when the heading's text, numbering and the tables of contents do not settle its level, so that how it is printed on its page has to decide it."
    )


class SkeletonLevels(BaseModel):
    """One level per heading of the document, judged from text alone.

    Attributes:
        levels: The level of each heading, one entry per heading.
    """

    levels: list[SkeletonLevel] = Field(
        description="The level of every heading of the document, one entry per heading, in any order."
    )
