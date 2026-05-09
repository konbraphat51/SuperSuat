from crewai import Agent, Task
from .State import DocumentAnalysis, SingleLayoutCheckResult


def create_heading_map_task(analyst: Agent) -> Task:
    return Task(
        name="Heading Map Task",
        description=(
            "Create a map of `heading level` -> `style description`"
            "Make level 1 heading as the title of the document."
            "Analyze the heading layouts of levels below 1, and and write a description of the layout style of the heading."
            "The description should be detailed enough for OCR agent to identify the"
        ),
        agent=analyst,  # type: ignore[arg-type]
        expected_output="A JSON object of the following format: {1: 'style description for level 1 heading', 2: 'style description for level 2 heading', ...}",
        output_pydantic=DocumentAnalysis,
    )


def create_layout_check_task(layout_checker: Agent) -> Task:
    return Task(
        name="Layout Check Task",
        description=(
            "Check if there is a layout style that is not written in the layout analysis document given."
            "This agent have to answer if there is or not, and if there is, what it is."
            "Your answer will be sent to layout analysis agent to update the layout analysis document."
        ),
        agent=layout_checker,  # type: ignore[arg-type]
        expected_output="A JSON object with two fields: `has_unknown_layout` and `unknown_layout_description",
        output_pydantic=SingleLayoutCheckResult,
    )
