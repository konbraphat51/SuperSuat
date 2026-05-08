from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, task, crew
from crewai.agents.agent_builder.base_agent import BaseAgent
from .State import SingleLayoutCheckResult

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
    
    @task
    def layout_check_task(self) -> Task:
        return Task(
            name = "Layout Check Task",
            description = (
                "Check if there is a layout style that is not written in the layout analysis document given."
                "This agent have to answer if there is or not, and if there is, what it is."
                "Your answer will be sent to layout analysis agent to update the layout analysis document."
            ),
            agent = self.layout_checker(),  # type: ignore[arg-type]
            expected_output="A JSON object with two fields: `has_unknown_layout` and `unknown_layout_description",                
            output_pydantic=SingleLayoutCheckResult
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            name="Single Analysis Crew",
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential
        )
