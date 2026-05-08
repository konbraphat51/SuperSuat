from crewai import Agent, Task, agent
from crewai.project import CrewBase, agent, tool
from crewai.agents.agent_builder.base_agent import BaseAgent
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

@CrewBase
class OcrCrew:
    agents: list[BaseAgent]
    tasks: list[Task]

    @tool
    def check_clip_tool(self) -> CheckClipTool:
        return CheckClipTool()

    @agent
    def ocr_agent(self) -> Agent:
        return Agent(
            role = "OCR Agent for single page",
            backstory = (
                "This entire project aims to conduct OCR on the PDF document and convert it into Markdown file."
                "This agent is responsible for conducting OCR for a single page of the PDF document, based on the layout analysis document created by the analyst agent."
                "Before conducting OCR, an analysis agent conducted a layout analysis to unify the heading levels",
                "This agent will receive the layout analysis document and the page to be OCRed."
                "This agent is responsible for conducting OCR for the page based on the layout analysis document, and output the OCR result in a structured format."
            ),
            goal = (
                "Conduct OCR for all information written in the given PDF page."
            ),
            llm = "bedrock/qwen.qwen3-vl-235b-a22b",
            allow_delegation = True,
            max_iter=30,
            multimodal = True,
        )

    @agent
    def crop_agent(self) -> Agent:
        return Agent(
            role = "Clipping the specified figure from the page",
            backstory = (
                "The entire project aims to conduct OCR on the PDF document and convert it into Markdown file."
                "The main OCR agent will delegate the task of clipping the figure from the page to this agent when it encounters a figure that needs to be clipped."
            ),
            goal = (
                "Return the bounding box of the figure specified by the main OCR agent, and crop the figure from the page and return the image data of the cropped figure."
                "Use `check_clip` tool to check if you clipped appropriately. If not, adjust the bounding box and clip again until you get it right."
            ),
            llm = "bedrock/qwen.qwen3-vl-235b-a22b",
            allow_delegation = False,
            max_iter = 10,
            multimodal = True,
            tools = [self.check_clip_tool()] # type: ignore[list-item]
        )
