"""Data models for document elements."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from docling_core.types.doc import DocItemLabel


class ElementType(str, Enum):
    """Types of document elements."""
    TEXT = "text"
    EQUATION = "equation"
    FIGURE = "figure"
    TABLE = "table"


@dataclass
class TextElement:
    """Represents a text element in the document."""
    reading_order: int
    content: str
    label: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": ElementType.TEXT.value,
            "content": self.content,
            "label": self.label,
            "reading_order": self.reading_order,
        }


@dataclass
class ImageElement:
    """Represents an image element (equation, figure, or table)."""
    reading_order: int
    element_type: ElementType
    filename: str
    exported: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.element_type.value,
            "filename": self.filename,
            "reading_order": self.reading_order,
            "exported": self.exported,
        }


# Type alias for document elements
DocumentElement = TextElement | ImageElement


@dataclass
class PageData:
    """Represents a page with its elements."""
    page_number: int
    elements: list[DocumentElement] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_number": self.page_number,
            "elements": [elem.to_dict() for elem in self.elements],
        }


@dataclass
class DocumentOutput:
    """Output data structure for the processed document."""
    source_pdf: str
    pages: list[PageData] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_pdf": self.source_pdf,
            "pages": [page.to_dict() for page in self.pages],
        }


class LabelMapper:
    """Maps Docling labels to element types.
    
    Image elements (FORMULA, PICTURE, TABLE, CHART) are exported as PNG files
    because they contain visual content that cannot be represented as plain text.
    All other elements are treated as text elements.
    """
    
    # Labels that represent visual/image content to be exported as PNG
    IMAGE_LABELS = frozenset([DocItemLabel.FORMULA, DocItemLabel.PICTURE, DocItemLabel.TABLE, DocItemLabel.CHART])
    
    # Mapping from Docling labels to our ElementType enum
    LABEL_TO_TYPE = {
        DocItemLabel.FORMULA: ElementType.EQUATION,
        DocItemLabel.PICTURE: ElementType.FIGURE,
        DocItemLabel.CHART: ElementType.FIGURE,
        DocItemLabel.TABLE: ElementType.TABLE,
    }

    @classmethod
    def is_image_element(cls, label: DocItemLabel) -> bool:
        """Check if label represents an image element."""
        return label in cls.IMAGE_LABELS

    @classmethod
    def get_element_type(cls, label: DocItemLabel) -> ElementType:
        """Get ElementType from DocItemLabel."""
        return cls.LABEL_TO_TYPE.get(label, ElementType.TEXT)
