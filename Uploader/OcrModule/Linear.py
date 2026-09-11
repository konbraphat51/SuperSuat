from dataclasses import dataclass
from PIL.Image import Image
from .Ocr import Ocr
from .OcrSchema import OcrResult, OcrResultSection

def call_agent():
    pass

class LinearOcr(Ocr):
    @dataclass
    class AgentMemory:
        header_page: list[int]

    def __init__(self):
        self.agent_memory = self.AgentMemory(
            header_page=[]
        )
        self.entire_section = OcrResultSection(
            block_type="section",
            section_content=[],
            child_sections=[]
        )

    def ocr(
        self,
        image_data: list[Image],
    ) -> OcrResult:
        # TODO
        pass

    def read_page(
        self,
        current_page: int,
    ) -> OcrResultSection:
        pass
        #call_agent()        
