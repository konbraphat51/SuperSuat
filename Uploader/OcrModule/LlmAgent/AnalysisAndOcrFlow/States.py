from typing import TypedDict
from PIL.Image import Image

class AnalysisState(TypedDict):
    # =inputs=
    images_num: int
    viewed_pages: list[int] # 1-indexed

    # =outputs=
    heading_style_map: dict[int, str]
    "1-indexed heading -> style description"

    chapter_starting_pages: dict[str, int] # 1-indexed
    "chapter name -> 1-indexed starting page"
