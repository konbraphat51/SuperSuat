from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain.agents import create_agent
from .Tools import LinearTools
from .prompt import OCR_AGENT_SYSTEM_PROMPT
from ..OcrSchema import OcrResultSection
from ..LlmHelper import ImageBase64, ImageMessageBuilder, build_ocr_context_string

# LangGraph counts one step per node, so a tool call costs two. This caps a
# single page at roughly 50 tool calls; without it the default limit of ~10000
# lets an agent stuck in a loop spend thousands of model calls before failing.
RECURSION_LIMIT = 100

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

        ocr_data_json = build_ocr_context_string(self.entire_section, page_number)
        page_image_content = self.linear_tools.get_page_image(page_number)

        result = self.agent.invoke(
            {
                "messages": [
                    HumanMessage(content=[
                        {
                            "type": "text",
                            "text": f"Here is the OCR data collected so far, as JSON:\n{ocr_data_json}",
                        },
                        *page_image_content,
                    ])
                ]
            },
            config={"recursion_limit": RECURSION_LIMIT},
        )

        last_message = result["messages"][-1]
        if getattr(last_message, "tool_calls", None):
            raise RuntimeError(f"Page {page_number}: agent stopped with pending tool calls")
