import json
from typing import Any

from ..BoundingBoxAgent import BoundingBoxAgent
from .Document import LinearDocument
from .Messages import image_message
from .Pages import PageImages
from .Tools import ADD_BLOCK, DELEGATE_BOUNDING_BOX, EDIT_BLOCK, GET_PAGE_IMAGE


class ToolRunner:
    """Runs the tool calls of the OCR agent against the document."""

    def __init__(
        self,
        document: LinearDocument,
        pages: PageImages,
        bounding_box_agent: BoundingBoxAgent,
    ) -> None:
        self.document = document
        self.pages = pages
        self.bounding_box_agent = bounding_box_agent

    def call(
        self,
        name: str,
        raw_arguments: str,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Run one tool call. Returns its result and the messages to append after it.

        Failures are reported to the agent as text so that it can correct itself.
        """
        try:
            arguments = json.loads(raw_arguments or "{}")
        except json.JSONDecodeError as error:
            return f"Error: the arguments are not valid JSON: {error}", []

        try:
            if name == GET_PAGE_IMAGE:
                return self._get_page_image(arguments)
            if name == EDIT_BLOCK:
                return self._edit_block(arguments), []
            if name == ADD_BLOCK:
                return self._add_block(arguments), []
            if name == DELEGATE_BOUNDING_BOX:
                return self._delegate_bounding_box(arguments), []
        except (KeyError, ValueError) as error:
            return f"Error: {error}", []

        return f"Error: unknown tool `{name}`.", []

    def _get_page_image(
        self,
        arguments: dict[str, Any],
    ) -> tuple[str, list[dict[str, Any]]]:
        page_index = self.pages.resolve(arguments["page_index"])
        return (
            f"The image of page {page_index} is attached in the next message.",
            [image_message(self.pages.get(page_index))],
        )

    def _edit_block(self, arguments: dict[str, Any]) -> str:
        block_index = arguments["block_index"]
        edited = self.document.edit_block(block_index, arguments)
        return f"Edited {', '.join(edited)} of the block {block_index}."

    def _add_block(self, arguments: dict[str, Any]) -> str:
        section_id = arguments["section_id"]
        block_type = arguments["block_type"]
        existing_pages = list(arguments["existing_pages"])

        if block_type == "text":
            if "text" not in arguments:
                raise ValueError("`text` is required for a text block.")
            block_index = self.document.add_text_block(
                section_id=section_id,
                existing_pages=existing_pages,
                text=arguments["text"],
                text_type=arguments.get("text_type", "paragraph"),
            )
        elif block_type == "image":
            page_index = arguments.get(
                "page_index", existing_pages[0] if existing_pages else 0
            )
            block_index = self.document.add_image_block(
                section_id=section_id,
                existing_pages=existing_pages,
                image_data=self.pages.clip(page_index, arguments.get("bounding_box")),
                caption=arguments.get("caption", ""),
            )
        else:
            raise ValueError(f"unknown block type `{block_type}`.")

        return (
            f"Added a {block_type} block to the section {section_id}. "
            f"Its index is {block_index}."
        )

    def _delegate_bounding_box(self, arguments: dict[str, Any]) -> str:
        page_index = self.pages.resolve(arguments["page_index"])
        bounding_box = self.bounding_box_agent.generate_bounding_box(
            self.pages.get(page_index), arguments["order"]
        )

        return json.dumps(
            {
                "page_index": page_index,
                "x": bounding_box.x,
                "y": bounding_box.y,
                "width": bounding_box.width,
                "height": bounding_box.height,
            }
        )
