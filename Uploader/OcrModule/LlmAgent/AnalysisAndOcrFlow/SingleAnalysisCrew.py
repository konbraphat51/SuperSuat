from crewai import Agent, Task
from crewai.project import CrewBase, agent
from crewai.agents.agent_builder.base_agent import BaseAgent


@CrewBase
class SingleAnalysisCrew:
    agents: list[BaseAgent]
    tasks: list[Task]

    @agent
    def layout_checker(self) -> Agent:
        return Agent(
            role = "Checking unknown layout style",
            backstory = (
                "This entire project aims to conduct OCR on the PDF document and convert it into Markdown file."
                "A PDF layout analyst agent analyzed the PDF layout, and created a map of heading level to style description."
                "However there might be some unknown layout style that the analyst agent have not seen, because the analyst agent did not read all pages."
                "This agent is responsible for checking if there is any unknown layout style for the given page before conducting OCR for this page."
            ),
            goal = (
                "Check if there is a layout style that is not written in the layout analysis document given."
                "This agent have to answer if there is or not, and if there is, what it is."
                "Your answer will be sent to layout analysis agent to update the layout analysis document."
            ),
            llm = "bedrock/qwen.qwen3-vl-235b-a22b",
            allow_delegation = False,
            max_iter = 10,
            multimodal = True,
        )
    
