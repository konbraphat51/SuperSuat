from crewai import Agent
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


def create_analyst() -> Agent:
    return Agent(
        role="PDF Layout Analyst",
        goal=(
            "Create a map of `heading level` -> `style description`"
            "Make level 1 heading as the title of the document."
            "Analyze the heading layouts of levels below 1, and and write a description of the layout style of the heading."
            "The description should be detailed enough for OCR agent to identify the heading in the actual OCR process."
        ),
        backstory=(
            "This entire project aims to conduct OCR on the PDF document and convert it into Markdown file."
            "This agent is responsible for analyzing PDF layout before actual OCR process."
        ),
        llm="bedrock/qwen.qwen3-vl-235b-a22b",
        allow_delegation=False,
        max_iter=50,
        multimodal=True,
    )


def create_layout_checker() -> Agent:
    return Agent(
        role="Checking unknown layout style",
        backstory=(
            "This entire project aims to conduct OCR on the PDF document and convert it into Markdown file."
            "A PDF layout analyst agent analyzed the PDF layout, and created a map of heading level to style description."
            "However there might be some unknown layout style that the analyst agent have not seen, because the analyst agent did not read all pages."
            "This agent is responsible for checking if there is any unknown layout style for the given page before conducting OCR for this page."
        ),
        goal=(
            "Check if there is a layout style that is not written in the layout analysis document given."
            "This agent have to answer if there is or not, and if there is, what it is."
            "Your answer will be sent to layout analysis agent to update the layout analysis document."
        ),
        llm="bedrock/qwen.qwen3-vl-235b-a22b",
        allow_delegation=False,
        max_iter=10,
        multimodal=True,
    )


def create_ocr_agent() -> Agent:
    return Agent(
        role="OCR Agent for single page",
        backstory=(
            "This entire project aims to conduct OCR on the PDF document and convert it into Markdown file."
            "This agent is responsible for conducting OCR for a single page of the PDF document, based on the layout analysis document created by the analyst agent."
            "Before conducting OCR, an analysis agent conducted a layout analysis to unify the heading levels",
            "This agent will receive the layout analysis document and the page to be OCRed."
            "This agent is responsible for conducting OCR for the page based on the layout analysis document, and output the OCR result in a structured format."
        ),
        goal=(
            "Conduct OCR for all information written in the given PDF page."
        ),
        llm="bedrock/qwen.qwen3-vl-235b-a22b",
        allow_delegation=True,
        max_iter=30,
        multimodal=True,
    )


def create_crop_agent(check_clip_tool: CheckClipTool) -> Agent:
    return Agent(
        role="Clipping the specified figure from the page",
        backstory=(
            "The entire project aims to conduct OCR on the PDF document and convert it into Markdown file."
            "The main OCR agent will delegate the task of clipping the figure from the page to this agent when it encounters a figure that needs to be clipped."
        ),
        goal=(
            "Return the bounding box of the figure specified by the main OCR agent, and crop the figure from the page and return the image data of the cropped figure."
            "Use `check_clip` tool to check if you clipped appropriately. If not, adjust the bounding box and clip again until you get it right."
        ),
        llm="bedrock/qwen.qwen3-vl-235b-a22b",
        allow_delegation=False,
        max_iter=10,
        multimodal=True,
        tools=[check_clip_tool],  # type: ignore[list-item]
    )
