from crewai import Crew, Agent, Task
from crewai.project import CrewBase, agent
from crewai.agents.agent_builder.base_agent import BaseAgent

@CrewBase
class OcrCrew:
    agents: list[BaseAgent]
    tasks: list[Task]
