from crewai import Agent, Task, agent
from crewai.project import CrewBase, agent
from crewai.agents.agent_builder.base_agent import BaseAgent

@CrewBase
class OcrCrew:
    agents: list[BaseAgent]
    tasks: list[Task]

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
