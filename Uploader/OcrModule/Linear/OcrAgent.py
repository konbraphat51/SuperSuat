import json
from dataclasses import asdict
from PIL.Image import Image
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from langgraph.prebuilt import create_react_agent
from .Tools import LinearTools
from .prompt import OCR_AGENT_SYSTEM_PROMPT
from ..OcrSchema import OcrResultSection

class OcrAgent:
    def __init__(
        self,
        ocr_model: BaseChatModel,
        linear_tools: LinearTools,
        entire_section: OcrResultSection,
        tools: list[BaseTool],
    ) -> None:
        self.ocr_model = ocr_model
        self.linear_tools = linear_tools
        self.entire_section = entire_section
        self.tools = tools

    def read_page(
        self,
        page_number: int,
    ) -> None:
        self.linear_tools.set_current_page(page_number)

        agent = create_react_agent(
            self.ocr_model,
            self.tools,
            prompt=OCR_AGENT_SYSTEM_PROMPT,
        )

        ocr_data_json = json.dumps(asdict(self.entire_section), ensure_ascii=False, indent=2)
        page_image_content = self.linear_tools.get_page_image(page_number)

        agent.invoke({
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
