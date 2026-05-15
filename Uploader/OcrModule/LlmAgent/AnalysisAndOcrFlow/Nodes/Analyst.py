from typing import Any
from pydantic import BaseModel, Field
from langchain.agents import create_agent  # type: ignore[import]
from langchain.agents.structured_output import ToolStrategy
from langchain.messages import SystemMessage  # type: ignore[import]
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import BaseMessage
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


class FirstOutputSchema(BaseModel):
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
        response_format=ToolStrategy(FirstOutputSchema),
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
            "version": state.get("version", 0) + 1,
        }
    }


REVIEW_USER_PROMPT = (
    "Some pages have been flagged as having unknown layout styles not covered by the current analysis. "
    "Review the flagged pages below and update the heading style map and OCR rules as needed. "
    "If the heading level numbering changes, provide a transition mapping (old level -> new level).\n\n"
    "Flagged pages:\n{failed_pages}"
)


class ReviewOutputSchema(BaseModel):
    heading_style_map: dict[int, str] = Field(
        description="Updated 1-indexed heading level -> style description mapping."
    )
    ocr_rules: str = Field(description="Updated unified OCR rule description.")
    heading_level_transition: dict[int, int] | None = Field(
        default=None,
        description=(
            "If heading level numbers changed, map old level -> new level. "
            "Omit or null if numbering is unchanged."
        ),
    )


async def analyst_review_node(
    state_graph: GraphState, config: RunnableConfig
) -> dict[str, Any]:
    # receive input
    state: AnalysisState = state_graph["analysis"]
    page_check_results = state_graph["page_check_results"]

    # sanity check
    if len(page_check_results) == 0:
        raise ValueError(
            "page_check_results is required in state_graph for analyst_review_node"
        )

    # prepare agent
    agent = create_agent(  # type: ignore[no-untyped-call]
        ANALYST_VLM,
        tools=[make_fetch_tool(state["images"])],
        response_format=ToolStrategy(ReviewOutputSchema),
    )

    # prepare review message
    failed_pages_text = "\n".join(
        f"- Page {result['page_num']}: {result['unknown_layout_styles']}"
        for result in page_check_results
    )
    review_message: BaseMessage = SystemMessage(
        content=REVIEW_USER_PROMPT.format(failed_pages=failed_pages_text)
    )
    messages = state["messages"] + [review_message]

    # run
    result = await agent.ainvoke(  # type: ignore[no-untyped-call]
        {"messages": messages}  # type: ignore[no-untyped-call]
    )
    structured: ReviewOutputSchema = result["structured_response"]

    # update version
    new_version = state.get("version", 0) + 1

    # receive history
    change_history: dict[int, dict[int, int]] = dict(
        state.get("heading_style_map_change_history", {})
    )
    if structured.heading_level_transition:
        change_history[new_version] = structured.heading_level_transition

    return {
        "analysis": {
            "messages": messages + result["messages"],
            "heading_style_map": structured.heading_style_map,
            "ocr_rules": structured.ocr_rules,
            "heading_style_map_change_history": change_history,
            "version": new_version,
        },
        "page_check_results": [],
    }
