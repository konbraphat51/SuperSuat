from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task, tool
from crewai.agents.agent_builder.base_agent import BaseAgent
from .Agents import CheckClipTool, create_analyst, create_crop_agent, create_layout_checker, create_ocr_agent
from .Tasks import create_heading_map_task, create_layout_check_task


@CrewBase
class AnalysisCrew:
    agents: list[BaseAgent]
    tasks: list[Task]

    @agent
    def analyst(self) -> Agent:
        return create_analyst()

    @task
    def heading_map_task(self) -> Task:
        return create_heading_map_task(self.analyst())

    @crew
    def crew(self) -> Crew:
        return Crew(
            name="Analysis Crew",
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
        )


@CrewBase
class SingleAnalysisCrew:
    agents: list[BaseAgent]
    tasks: list[Task]

    @agent
    def layout_checker(self) -> Agent:
        return create_layout_checker()

    @task
    def layout_check_task(self) -> Task:
        return create_layout_check_task(self.layout_checker())

    @crew
    def crew(self) -> Crew:
        return Crew(
            name="Single Analysis Crew",
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
        )


@CrewBase
class OcrCrew:
    agents: list[BaseAgent]
    tasks: list[Task]

    @tool
    def check_clip_tool(self) -> CheckClipTool:
        return CheckClipTool()

    @agent
    def ocr_agent(self) -> Agent:
        return create_ocr_agent()

    @agent
    def crop_agent(self) -> Agent:
        return create_crop_agent(self.check_clip_tool())
