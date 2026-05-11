from typing import Any
from pydantic import BaseModel, Field
from langchain.agents import create_agent  # type: ignore[import]
from langchain.agents.structured_output import ToolStrategy
from langchain.messages import SystemMessage  # type: ignore[import]
from langchain_core.runnables import RunnableConfig
from ..CommonTools import make_fetch_tool
from ..States import AnalysisState, GraphState
from ..Clients import ANALYST_VLM

FIRST_SYSTEM_PROMPT = (
    "This entire project is to conduct OCR on scanned PDF documents. "
    "\nYour role is to analyze the layout of the document "
    "before the actual OCR in order that the format of each OCR agent can be unified."
    "\nSpecify the page and retrieve the image of the page."
    "\nCreate a mapping of heading styles and their corresponding page numbers."
    "Individual OCR agents for each single page will refer this mapping to determine the heading level,"
    "so be sure to include all the heading styles and give a clear description for each style "
    "so that the OCR agents can easily understand and identify them, "
    "and the heading levels are unified across the entire document."
    "\nAlso, if the OCR result may be affected by the layout of the page, "
    "define a unified OCR rule description to extract main text that can be referred by all the OCR agents for each page."
    "For example, if there is book title in the header of all pages, "
    "the OCR rule should specify to ignore the text in the header when extracting main text. "
)


class OutputSchema(BaseModel):
    heading_style_map: dict[int, str] = Field(
        description=(
            "1-indexed heading level -> style description."
            "level 1 is for document title."
        )
    )

    ocr_rules: str = Field(
        description=(
            "A unified OCR rule description that can be referred by all the OCR agents for each page."
        )
    )


async def first_analyst_node(
    state_graph: GraphState, config: RunnableConfig
) -> dict[str, Any]:
    state: AnalysisState = state_graph["analysis"]

    agent = create_agent(  # type: ignore[no-untyped-call]
        ANALYST_VLM,
        tools=[make_fetch_tool(state["images"])],
        response_format=ToolStrategy(OutputSchema),
    )

    messages = [SystemMessage(content=FIRST_SYSTEM_PROMPT)]

    result = await agent.ainvoke(  # type: ignore[no-untyped-call]
        {"messages": messages}  # type: ignore[no-untyped-call]
    )

    return {
        "analysis": {
            "messages": result["messages"],
            "heading_style_map": result[
                "structured_response"
            ].heading_style_map,
            "ocr_rules": result["structured_response"].ocr_rules,
        }
    }
