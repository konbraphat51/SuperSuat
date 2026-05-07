from crewai import Agent
from crewai.project import CrewBase, agent

@CrewBase
class AnalysisCrew:
    @agent
    def analyst(self) -> Agent:
        return Agent(
            role = "PDF Layout Analyst",
            goal = (
                "Create a map of `heading level` -> `style description`"
                "Make level 1 heading as the title of the document."
                "Analyze the heading layouts of levels below 1, and and write a description of the layout style of the heading."
                "The description should be detailed enough for OCR agent to identify the heading in the actual OCR process."
            ),
            backstory = (
                "This entire project aims to conduct OCR on the PDF document and convert it into Markdown file."
                "This agent is responsible for analyzing PDF layout before actual OCR process."
            ),
            llm = "bedrock/qwen.qwen3-vl-235b-a22b",
            allow_delegation = False,
            max_iter = 50,
            multimodal = True
        )
