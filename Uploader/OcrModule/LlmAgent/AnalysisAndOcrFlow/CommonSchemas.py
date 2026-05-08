from pydantic import BaseModel, Field

class PageImage(BaseModel):
    """
    Schema for representing a page image.
    """

    page_number: int = Field(description="The page number of the image. Starts from 1.")
    base64_data: str = Field(description="The base64-encoded string of the page image.")
