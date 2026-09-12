import json
import logging
from PIL.Image import Image
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain.agents import create_agent
from langgraph.errors import GraphRecursionError
from .Tools import LinearTools, build_context_dict
from .prompt import OCR_AGENT_SYSTEM_PROMPT
from ..OcrSchema import OcrResultSection

logger = logging.getLogger(__name__)

class OcrAgent:
    def __init__(
        self,
        ocr_model: BaseChatModel,
        clipper_model: BaseChatModel,
        all_page_images: list[Image],
        entire_section: OcrResultSection,
    ) -> None:
        self.ocr_model = ocr_model
        self.entire_section = entire_section
        self._initialize_tools(all_page_images, clipper_model)
        self._initialize_agent()

    def _initialize_tools(
        self,
        all_page_images: list[Image],
        clipper_model: BaseChatModel,
    ) -> None:
        self.linear_tools = LinearTools(
            all_page_images=all_page_images,
            ocr_entire_section=self.entire_section,
            clipper_model=clipper_model,
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
    ) -> bool:
        """Process the given page. Returns whether the page was fully processed."""
        self.linear_tools.set_current_page(page_number)

        context_dict = build_context_dict(self.entire_section, page_number)
        ocr_data_json = json.dumps(context_dict, ensure_ascii=False, indent=2)
        page_image_content = self.linear_tools.get_page_image(page_number)

        try:
            result = self.agent.invoke({
                "messages": [
                    HumanMessage(content=[
                        {
                            "type": "text",
                            "text": f"Here is the OCR data collected so far, as JSON:\n{ocr_data_json}",
                        },
                        *page_image_content,
                    ])
                ]
            })
        except GraphRecursionError:
            logger.error(f"Page {page_number}: agent hit the recursion limit before finishing")
            return False
        except Exception:
            logger.exception(f"Page {page_number}: agent run failed")
            return False

        last_message = result["messages"][-1]
        if getattr(last_message, "tool_calls", None):
            logger.warning(f"Page {page_number}: agent stopped with pending tool calls")
            return False

        return True
