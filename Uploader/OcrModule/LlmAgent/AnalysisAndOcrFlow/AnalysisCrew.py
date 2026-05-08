from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from .State import DocumentAnalysis

# class HeadingMapTaskOutput(BaseModel):
#     heading_style_map: dict[int, str] = Field(
#         description="A map of heading level to style description. For example, {1: 'bold and centered', 2: 'bold and left-aligned', ...}"
#     )


@CrewBase
class AnalysisCrew:
    agents: list[BaseAgent]
    tasks: list[Task]

    @agent
    def analyst(self) -> Agent:
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

    @task
    def heading_map_task(self) -> Task:
        return Task(
            name="Heading Map Task",
            description=(
                "Create a map of `heading level` -> `style description`"
                "Make level 1 heading as the title of the document."
                "Analyze the heading layouts of levels below 1, and and write a description of the layout style of the heading."
                "The description should be detailed enough for OCR agent to identify the"
            ),
            agent=self.analyst(),  # type: ignore[arg-type]
            expected_output="A JSON object of the following format: {1: 'style description for level 1 heading', 2: 'style description for level 2 heading', ...}",
            output_pydantic=DocumentAnalysis,  # HeadingMapTaskOutput,
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            name="Analysis Crew",
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
        )
