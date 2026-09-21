import logging
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain.agents import create_agent
from .OcrOutputSchema import OutputSchema
from .Tools import LinearTools
from .prompt import OCR_AGENT_SYSTEM_PROMPT
from ..OcrSchema import OcrResultSection
from ..LlmHelper import (
    ImageBase64,
    ImageMessageBuilder,
    build_ocr_context_string,
    log_agent_message,
)

logger = logging.getLogger(__name__)

RECURSION_LIMIT = 20


class OcrAgent:
    def __init__(
        self,
        ocr_model: BaseChatModel,
        clipper_model: BaseChatModel,
        all_pages: list[ImageBase64],
        entire_section: OcrResultSection,
        image_message_builder: ImageMessageBuilder,
    ) -> None:
        self.entire_section = entire_section
        self._initialize_tools(all_pages, clipper_model, image_message_builder)
        self._initialize_agent(ocr_model)

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
            tool(self.linear_tools.clip_image),
        ]

    def _initialize_agent(self, ocr_model: BaseChatModel) -> None:
        self.agent = create_agent(
            ocr_model,
            self.tools,
            system_prompt=OCR_AGENT_SYSTEM_PROMPT,
            response_format=OutputSchema,
        )

    def read_page(
        self,
        page_number: int,
    ) -> OutputSchema:
        """Reads one page and returns every edit it needs, as a single
        OutputSchema. Applying that to the document tree is the caller's job
        (see OcrDataEditor) - this class only produces it."""
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

        for message in result["messages"]:
            log_agent_message(f"page {page_number}", message)

        structured_response = result.get("structured_response")
        if structured_response is None:
            raise RuntimeError(
                f"Page {page_number}: agent finished without a structured response"
            )

        logger.info("page %d | done", page_number)

        return structured_response
