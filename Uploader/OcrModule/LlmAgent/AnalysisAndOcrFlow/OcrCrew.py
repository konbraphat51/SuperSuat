from crewai import Task
from crewai.project import CrewBase
from crewai.agents.agent_builder.base_agent import BaseAgent

@CrewBase
class OcrCrew:
    agents: list[BaseAgent]
    tasks: list[Task]
