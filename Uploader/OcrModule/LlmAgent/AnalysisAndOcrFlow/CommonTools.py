import io
import base64
from typing import Any
from PIL.Image import Image
from langchain.messages import ToolMessage
from langgraph.types import Command
from langchain.tools import BaseTool, ToolRuntime, tool   # type: ignore[import]
from pymupdf import f  # type: ignore[import]


def make_fetch_tool(
    page_images: list[Image]
) -> BaseTool:
    
    # define the tool function
    @tool("fetch_pages_image", return_direct=False)
    def fetch_pages_image(
        page_nums: list[int],
        runtime: ToolRuntime[None, Any]  
    ) -> Command[Any]:
        # Add ToolMessage adding image data
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=[
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "data": _convert_image_to_base64(page_images[page_num - 1]),
                                    "media_type": "image/png"
                                }
                            },
                            {
                                "type": "text",
                                "text": f"Page {page_num} image"
                            }
                        ],
                        tool_call_id=runtime.tool_call_id,
                        name="fetch_pages_image"
                    ) for page_num in page_nums
                ]
            }
        )
    
    return fetch_pages_image
    
# return base64
def _convert_image_to_base64(image: Image) -> str:
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str
