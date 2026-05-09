import operator
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage

from ..States import AnalysisState

# Subgraph of Analyst Node <-> Page Image Fetcher Tool Node

class AnalystInnerState(TypedDict):
    messages: Annotated[
        list[BaseMessage],
        operator.add
    ]

async def first_analyst_node(
    state: AnalysisState
) -> AnalysisState:
    # TODO: run subgraph
    raise NotImplementedError()

