import base64
from dataclasses import dataclass
from io import BytesIO
from PIL.Image import Image


@dataclass
class ImageBase64:
    b64: str
    size: tuple[int, int] # (width, height)

def pil_to_base64(img: Image, format: str = "PNG") -> str:
    buffered = BytesIO()
    img.save(buffered, format=format)
    return base64.b64encode(buffered.getvalue()).decode("utf-8")
