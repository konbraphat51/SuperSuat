"""Reading one page: the agent run that reports what the page needs."""

import logging
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain.agents import create_agent
from .OcrDataEditor import validate_output
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

# LangGraph counts one step per node, so a tool call costs two. Only
# get_page_image and clip_image are tool calls now, so this is a guard
# against a loop rather than a budget for a normal page.
RECURSION_LIMIT = 20

# how many times a rejected response may be handed back to the model to fix
MAX_OUTPUT_ATTEMPTS = 3


def _rejection_message(errors: list[str]) -> str:
    """What the model is told when its response can't be applied."""
    listed = "\n".join(f"- {error}" for error in errors)

    return (
        "Your response could not be applied, and nothing from it was recorded. "
        f"Fix these problems and report the whole page again:\n{listed}"
    )


class OcrAgent:
    """Runs one page through the OCR model and returns the operations it
    reports, checked against the document tree.

    The model gets two tools - looking at a page image, and locating a figure
    - and reports every edit the page needs in one structured final response,
    rather than one tool call per edit."""

    def __init__(
        self,
        ocr_model: BaseChatModel,
        clipper_model: BaseChatModel,
        all_pages: list[ImageBase64],
        entire_section: OcrResultSection,
        image_message_builder: ImageMessageBuilder,
        clipper_image_message_builder: ImageMessageBuilder | None = None,
    ) -> None:
        self.entire_section = entire_section
        self._initialize_tools(
            all_pages,
            clipper_model,
            image_message_builder,
            clipper_image_message_builder,
        )
        self._initialize_agent(ocr_model)

    def _initialize_tools(
        self,
        all_pages: list[ImageBase64],
        clipper_model: BaseChatModel,
        image_message_builder: ImageMessageBuilder,
        clipper_image_message_builder: ImageMessageBuilder | None,
    ) -> None:
        self.linear_tools = LinearTools(
            all_pages=all_pages,
            ocr_entire_section=self.entire_section,
            clipper_model=clipper_model,
            image_message_builder=image_message_builder,
            clipper_image_message_builder=clipper_image_message_builder,
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
        OutputSchema that has been checked against the document tree.
        Applying it is the caller's job (see OcrDataEditor) - this class only
        produces it, and hands a response the tree would reject back to the
        model to correct."""
        self.linear_tools.set_current_page(page_number)

        ocr_data_json = build_ocr_context_string(self.entire_section, page_number)
        page_image_content = self.linear_tools.get_page_image(page_number)

        logger.info("page %d | starting", page_number)

        messages = [
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
        logged_message_count = 0

        for attempt in range(1, MAX_OUTPUT_ATTEMPTS + 1):
            result = self.agent.invoke(
                {"messages": messages},
                config={"recursion_limit": RECURSION_LIMIT},
            )

            for message in result["messages"][logged_message_count:]:
                log_agent_message(f"page {page_number}", message)
            logged_message_count = len(result["messages"])

            structured_response = result.get("structured_response")
            if structured_response is None:
                raise RuntimeError(
                    f"Page {page_number}: agent finished without a structured response"
                )

            errors = validate_output(structured_response, self.entire_section)
            if not errors:
                logger.info("page %d | done", page_number)
                return structured_response

            logger.warning(
                "page %d | attempt %d/%d rejected: %s",
                page_number,
                attempt,
                MAX_OUTPUT_ATTEMPTS,
                "; ".join(errors),
            )
            messages = list(result["messages"]) + [
                HumanMessage(content=_rejection_message(errors))
            ]

        raise RuntimeError(
            f"Page {page_number}: the model's response still could not be applied "
            f"after {MAX_OUTPUT_ATTEMPTS} attempts: {'; '.join(errors)}"
        )
