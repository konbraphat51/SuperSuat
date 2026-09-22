"""Locating a figure on a page image, as a dedicated model call."""

import logging
from pydantic import BaseModel, Field
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from ..LlmHelper import build_image_message

logger = logging.getLogger(__name__)


class BoundingBoxOutput(BaseModel):
    """The region of a page image a clip request resolved to."""

    bounding_box: tuple[int, int, int, int] = Field(
        description="The bounding box of the clipped region in the image, as (x, y, width, height)."
    )


def clip_image_with_agent(
    clipper_model: BaseChatModel,
    order: str,
    img_b64: str,
    image_size: tuple[int, int],
) -> BoundingBoxOutput:
    """The bounding box of whatever `order` describes, clamped to the image.

    Its own model call rather than part of the OCR agent's response: a model
    reading a whole page at once places boxes far less accurately than one
    looking for a single figure."""
    width, height = image_size
    instruction = (
        f"{order}\n\n"
        f"The image is {width}x{height} pixels. Return the bounding box in pixel "
        f"coordinates (x, y, width, height) relative to the image's top-left corner, "
        f"with 0 <= x <= {width} and 0 <= y <= {height}."
    )

    structured_clipper_model = clipper_model.with_structured_output(BoundingBoxOutput)
    result = structured_clipper_model.invoke(
        [HumanMessage(content=build_image_message(instruction, img_b64))]
    )

    raw_bounding_box = result.bounding_box
    x, y, box_width, box_height = raw_bounding_box
    x = min(max(x, 0), width)
    y = min(max(y, 0), height)
    box_width = min(max(box_width, 0), width - x)
    box_height = min(max(box_height, 0), height - y)
    result.bounding_box = (x, y, box_width, box_height)

    logger.info(
        "clip order=%r raw_bounding_box=%s clamped_bounding_box=%s",
        order,
        raw_bounding_box,
        result.bounding_box,
    )

    return result
