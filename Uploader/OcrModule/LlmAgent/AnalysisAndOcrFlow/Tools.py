from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class CheckClipToolInput(BaseModel):
    bounding_box_left_top_x: float = Field(description="The x coordinate of the left top corner of the bounding box.")
    bounding_box_left_top_y: float = Field(description="The y coordinate of the left top corner of the bounding box.")
    bounding_box_right_bottom_x: float = Field(description="The x coordinate of the right bottom corner of the bounding box.")
    bounding_box_right_bottom_y: float = Field(description="The y coordinate of the right bottom corner of the bounding box.")


class CheckClipTool(BaseTool):
    name: str = "Check Clip"
    description: str = (
        "This tool returns image data clipped by the given bounding box coordinates from the page image"
        "This tool itself will return the path of the clipped image"
    )
    input_schema: type = CheckClipToolInput

    def _run(
        self,
        bounding_box_left_top_x: float,
        bounding_box_left_top_y: float,
        bounding_box_right_bottom_x: float,
        bounding_box_right_bottom_y: float,
    ) -> str:
        # TODO
        raise NotImplementedError("The actual clipping logic is not implemented yet. This is a placeholder implementation.")
