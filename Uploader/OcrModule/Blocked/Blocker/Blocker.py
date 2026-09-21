from abc import ABC, abstractmethod
from PIL.Image import Image
from ..Schema import Block, BlockerResult, BlockType

class Blocker(ABC):
    @abstractmethod
    def block(
        self,
        pages: list[Image],
    ) -> BlockerResult:
        """Detects blocks of text, math, images, and tables in the page images."""
        pass
