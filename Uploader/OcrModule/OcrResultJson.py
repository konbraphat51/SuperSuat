"""Writing an OcrResult out as JSON, and reading it back."""

import json
from dataclasses import asdict
from typing import Any

from OcrModule.OcrSchema import (
    OcrResult,
    OcrResultBlock,
    OcrResultBlockFigure,
    OcrResultBlockTableOfContents,
    OcrResultBlockText,
    OcrResultSection,
    TableOfContentsEntry,
)


def dump_ocr_result(result: OcrResult) -> str:
    """The document tree as indented JSON, its text left unescaped."""
    return json.dumps(asdict(result), ensure_ascii=False, indent=2)


def load_ocr_result(text: str) -> OcrResult:
    """The document tree written by dump_ocr_result, or by asdict() in the same shape."""
    root = _load_block(json.loads(text)["root_section"])
    if not isinstance(root, OcrResultSection):
        raise ValueError(f"The root is a {root.block_type}, not a section")
    return OcrResult(root_section=root)


def _load_block(data: dict[str, Any]) -> OcrResultBlock:
    """One block, with whatever is nested in it."""
    if data["block_type"] == "section":
        return OcrResultSection(
            block_type="section",
            existing_pages=data["existing_pages"],
            block_index=data["block_index"],
            section_content=[_load_block(child) for child in data["section_content"]],
        )
    if data["block_type"] == "figure":
        x, y, width, height = data["bounding_box"]
        return OcrResultBlockFigure(
            block_type="figure",
            existing_pages=data["existing_pages"],
            block_index=data["block_index"],
            page_index=data["page_index"],
            bounding_box=(x, y, width, height),
            caption=data["caption"],
        )
    if data["block_type"] == "table_of_contents":
        return OcrResultBlockTableOfContents(
            block_type="table_of_contents",
            existing_pages=data["existing_pages"],
            block_index=data["block_index"],
            entries=[_load_entry(entry) for entry in data["entries"]],
        )
    return OcrResultBlockText(
        block_type=data["block_type"],
        existing_pages=data["existing_pages"],
        block_index=data["block_index"],
        text=data["text"],
    )


def _load_entry(data: dict[str, Any]) -> TableOfContentsEntry:
    """One table of contents entry, with its children."""
    return TableOfContentsEntry(
        section_number=data["section_number"],
        title=data["title"],
        page_number=data["page_number"],
        children=[_load_entry(child) for child in data["children"]],
    )
