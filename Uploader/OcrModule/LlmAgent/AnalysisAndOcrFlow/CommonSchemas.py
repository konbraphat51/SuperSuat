from collections.abc import Callable
from pydantic import BaseModel, Field

class PageImage(BaseModel):
    """
    Schema for representing a page image.
    """

    page_number: int = Field(description="The page number of the image. Starts from 1.")
    base64_data: str = Field(description="The base64-encoded string of the page image.")

add_page_images: Callable[[list[PageImage], list[PageImage]], list[PageImage]] = lambda a, b: a + b
