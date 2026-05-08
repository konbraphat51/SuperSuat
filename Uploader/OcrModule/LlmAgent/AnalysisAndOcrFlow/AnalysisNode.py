from __future__ import annotations
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages  # type: ignore[import-untyped]
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from .CommonSchemas import PageImage, add_page_images

class AnalysisResult(BaseModel):
    """
    Output Schema
    """

    heading_styles: dict[int, str] = Field(
        description="A dictionary mapping heading levels to their corresponding styles descriptions."
    )

class State(TypedDict):
    """
    Node State
    """

    messages: Annotated[list[BaseMessage], add_messages]
    viewed_page_images: Annotated[list[PageImage], add_page_images]

    heading_styles: dict[int, str]
