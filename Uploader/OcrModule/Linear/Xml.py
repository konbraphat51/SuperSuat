from xml.sax.saxutils import escape, quoteattr

from ..OcrSchema import (
    OcrResultBlock,
    OcrResultBlockImage,
    OcrResultBlockText,
    OcrResultSection,
)

ROOT_SECTION_ID = "0"


def child_section_id(parent_id: str, index: int) -> str:
    """Id of the `index`-th child of the section `parent_id`."""
    return f"{parent_id}.{index}"


def section_to_xml(
    section: OcrResultSection,
    section_id: str = ROOT_SECTION_ID,
) -> str:
    """XML the OCR agent reads the document from, and addresses it by."""
    return "\n".join(_section_lines(section, section_id, 0))


def _section_lines(
    section: OcrResultSection,
    section_id: str,
    depth: int,
) -> list[str]:
    pad = "  " * depth
    lines = [f"{pad}<section id={quoteattr(section_id)}>"]

    for block in section.section_content:
        lines.append(_block_line(block, depth + 1))

    for index, child in enumerate(section.child_sections):
        lines.extend(
            _section_lines(child, child_section_id(section_id, index), depth + 1)
        )

    lines.append(f"{pad}</section>")
    return lines


def _block_line(block: OcrResultBlock, depth: int) -> str:
    pad = "  " * depth
    attributes = [
        f"index={quoteattr(str(block.block_index))}",
        f"type={quoteattr(block.block_type)}",
        f"pages={quoteattr(','.join(str(page) for page in block.existing_pages))}",
    ]
    body = ""

    if isinstance(block, OcrResultBlockText):
        attributes.append(f"text_type={quoteattr(block.text_type)}")
        body = escape(block.text)
    elif isinstance(block, OcrResultBlockImage):
        attributes.append(f"caption={quoteattr(block.caption)}")

    if not body:
        return f"{pad}<block {' '.join(attributes)} />"

    return f"{pad}<block {' '.join(attributes)}>{body}</block>"
