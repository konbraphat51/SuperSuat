from typing import Any

TEXT_TYPES = [
    "paragraph",
    "heading",
    "list_item",
    "document_index",
    "note",
    "code",
    "math",
]

GET_PAGE_IMAGE = "get_page_image"
EDIT_BLOCK = "edit_block"
ADD_BLOCK = "add_block"
DELEGATE_BOUNDING_BOX = "delegate_bounding_box"

OCR_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": GET_PAGE_IMAGE,
            "description": "Get the image of the specified page of the document.",
            "parameters": {
                "type": "object",
                "properties": {
                    "page_index": {
                        "type": "integer",
                        "description": "0-indexed page number.",
                    },
                },
                "required": ["page_index"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": EDIT_BLOCK,
            "description": (
                "Edit an existing block of the document. "
                "Only the given fields are overwritten."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "block_index": {
                        "type": "integer",
                        "description": "`index` attribute of the block to edit.",
                    },
                    "text": {
                        "type": "string",
                        "description": "New whole text of a text block.",
                    },
                    "text_type": {"type": "string", "enum": TEXT_TYPES},
                    "caption": {
                        "type": "string",
                        "description": "New caption of an image block.",
                    },
                    "existing_pages": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": (
                            "New whole list of 0-indexed pages the block appears on."
                        ),
                    },
                },
                "required": ["block_index"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": ADD_BLOCK,
            "description": (
                "Append a new block to the specified section. "
                "The block index is assigned by the system."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "section_id": {
                        "type": "string",
                        "description": "`id` attribute of the section to append to.",
                    },
                    "block_type": {"type": "string", "enum": ["text", "image"]},
                    "existing_pages": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "0-indexed pages the block appears on.",
                    },
                    "text": {
                        "type": "string",
                        "description": "Text of the block. Required for a text block.",
                    },
                    "text_type": {"type": "string", "enum": TEXT_TYPES},
                    "caption": {
                        "type": "string",
                        "description": "Caption of the block. For an image block.",
                    },
                    "page_index": {
                        "type": "integer",
                        "description": (
                            "For an image block: the page the figure is clipped from."
                        ),
                    },
                    "bounding_box": {
                        "type": "object",
                        "description": (
                            "For an image block: the area to clip, as returned by "
                            "`delegate_bounding_box`. The whole page is used if omitted."
                        ),
                        "properties": {
                            "x": {"type": "integer"},
                            "y": {"type": "integer"},
                            "width": {"type": "integer"},
                            "height": {"type": "integer"},
                        },
                        "required": ["x", "y", "width", "height"],
                    },
                },
                "required": ["section_id", "block_type", "existing_pages"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": DELEGATE_BOUNDING_BOX,
            "description": (
                "Ask the bounding box agent for the bounding box of an area "
                "of the specified page."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "page_index": {
                        "type": "integer",
                        "description": "0-indexed page the area is on.",
                    },
                    "order": {
                        "type": "string",
                        "description": (
                            "Description of the area to clip, precise enough for an "
                            "agent that only sees the page image."
                        ),
                    },
                },
                "required": ["page_index", "order"],
            },
        },
    },
]
