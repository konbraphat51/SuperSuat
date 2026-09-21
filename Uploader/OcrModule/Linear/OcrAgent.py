import logging
from pydantic import BaseModel, Field
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain.agents import create_agent
from .Tools import LinearTools
from .prompt import OCR_AGENT_SYSTEM_PROMPT
from ..OcrSchema import OcrResultSection, TEXT_BLOCK_TYPES
from ..LlmHelper import (
    ImageBase64,
    ImageMessageBuilder,
    build_ocr_context_string,
    log_agent_message,
)

logger = logging.getLogger(__name__)

# LangGraph counts one step per node, so a tool call costs two. This caps a
# single page at roughly 50 tool calls; without it the default limit of ~10000
# lets an agent stuck in a loop spend thousands of model calls before failing.
RECURSION_LIMIT = 100

class AddTextBlockInputSchema(BaseModel):
    """Add a new text block to the specified section."""

    section_block_index: int = Field(
        description="The block_index of the section to add this block into."
    )
    block_type: TEXT_BLOCK_TYPES = Field(
        description="The kind of text block this is."
    )
    text: str = Field(description="The block's text.")

class AddImageBlockInputSchema(BaseModel):
    """Add a new figure block to the specified section. bounding_box must be
    in the pixel coordinates of the current page."""

    section_block_index: int = Field(
        description="The block_index of the section to add this block into."
    )
    bounding_box: tuple[int, int, int, int] = Field(
        description="(x, y, width, height) of the figure, in the current page's pixel coordinates."
    )
    caption: str = Field(description="The figure's caption.")

class AddSectionInputSchema(BaseModel):
    """Add a new empty section under the specified parent section."""

    parent_section_block_index: int = Field(
        description="The block_index of the section to add this new section into."
    )

class EditBlockInputSchema(BaseModel):
    """Edit the text of an existing block by its index."""

    block_index: int = Field(description="The block_index of the block to edit.")
    text: str = Field(description="The block's new text.")

class OutputSchema(BaseModel):
    adding_text_block: list[AddTextBlockInputSchema] = []
    adding_image_block: list[AddImageBlockInputSchema] = []
    adding_section: list[AddSectionInputSchema] = []
    editing_block: list[EditBlockInputSchema] = []


class OcrAgent:
    def __init__(
        self,
        ocr_model: BaseChatModel,
        clipper_model: BaseChatModel,
        all_pages: list[ImageBase64],
        entire_section: OcrResultSection,
        image_message_builder: ImageMessageBuilder,
    ) -> None:
        self.ocr_model = ocr_model
        self.entire_section = entire_section
        self._initialize_tools(all_pages, clipper_model, image_message_builder)
        self._initialize_agent()

    def _initialize_tools(
        self,
        all_pages: list[ImageBase64],
        clipper_model: BaseChatModel,
        image_message_builder: ImageMessageBuilder,
    ) -> None:
        self.linear_tools = LinearTools(
            all_pages=all_pages,
            ocr_entire_section=self.entire_section,
            clipper_model=clipper_model,
            image_message_builder=image_message_builder,
        )

        self.tools = [
            tool(self.linear_tools.get_page_image),
            tool(self.linear_tools.edit_block),
            tool(self.linear_tools.add_text_block),
            tool(self.linear_tools.add_image_block),
            tool(self.linear_tools.add_section),
            tool(self.linear_tools.move_block),
            tool(self.linear_tools.clip_image),
        ]

    def _initialize_agent(self) -> None:
        self.agent = create_agent(
            self.ocr_model,
            self.tools,
            system_prompt=OCR_AGENT_SYSTEM_PROMPT,
        )

    def read_page(
        self,
        page_number: int,
    ) -> None:
        self.linear_tools.set_current_page(page_number)

        ocr_data_json = build_ocr_context_string(
            self.entire_section, page_number
        )
        page_image_content = self.linear_tools.get_page_image(page_number)

        logger.info("page %d | starting", page_number)

        result = self.agent.invoke(
            {
                "messages": [
                    HumanMessage(
                        content=[
                            {
                                "type": "text",
                                "text": f"Here is the OCR data collected so far, as JSON:\n{ocr_data_json}",
                            },
                            *page_image_content,
                        ]
                    )
                ]
            },
            config={"recursion_limit": RECURSION_LIMIT},
        )

        # Logged only once the page is fully done: log_agent_message is a
        # no-op for the HumanMessage this call started from, so this reports
        # every model message and tool call/result from the page in order.
        for message in result["messages"]:
            log_agent_message(f"page {page_number}", message)

        last_message = result["messages"][-1]
        if getattr(last_message, "tool_calls", None):
            raise RuntimeError(
                f"Page {page_number}: agent stopped with pending tool calls"
            )

        logger.info("page %d | done", page_number)
