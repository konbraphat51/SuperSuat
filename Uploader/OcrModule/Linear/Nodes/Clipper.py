from pydantic import BaseModel, Field
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage


class BoundingBoxOutput(BaseModel):
    bounding_box: tuple[int, int, int, int] = Field(
        description="The bounding box of the clipped region in the image, as (x, y, width, height)."
    )


def clip_image_with_agent(
    clipper_model: BaseChatModel,
    order: str,
    img_b64: str,
) -> BoundingBoxOutput:
    structured_clipper_model = clipper_model.with_structured_output(BoundingBoxOutput)
    return structured_clipper_model.invoke([
        HumanMessage(content=[
            {"type": "text", "text": order},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"},
            },
        ])
    ])
