from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Union
import xmltodict

__all__ = [
	"OriginItemType",
	"OriginItem",
	"OriginParagraph",
	"OriginFigure",
	"OriginData",
	"origin2xml",
	"xml2origin",
]


class OriginItemType(str, Enum):
	PARAGRAPH = "paragraph"
	FIGURE = "figure"


@dataclass(slots=True)
class OriginItem:
	index: int
	orderIndex: int
	type: OriginItemType

	def to_dict(self) -> dict:
		return {
			"type": self.type.value,
			"index": self.index,
			"orderIndex": self.orderIndex,
		}

	@staticmethod
	def from_dict(d: dict) -> "OriginItem":
		try:
			item_type = OriginItemType(d["type"])
		except KeyError as e:
			raise ValueError("Missing 'type' field in item") from e
		except ValueError as e:
			raise ValueError(f"Unknown OriginItem type '{d.get('type')}'") from e
		common = dict(
			index=int(d["index"]),
			orderIndex=int(d["orderIndex"]),
			type=item_type,
		)
		if item_type is OriginItemType.PARAGRAPH:
			return OriginParagraph(content=d.get("content", ""), **common)
		if item_type is OriginItemType.FIGURE:
			return OriginFigure(imageId=d.get("imageId", ""), caption=d.get("caption", ""), **common)
		raise AssertionError(f"Unhandled item type {item_type}")


@dataclass(slots=True)
class OriginParagraph(OriginItem):
	content: str

	def to_dict(self) -> dict:  # type: ignore[override]
		d = OriginItem.to_dict(self)
		d["content"] = self.content
		return d


@dataclass(slots=True)
class OriginFigure(OriginItem):
	imageId: str
	caption: str

	def to_dict(self) -> dict:  # type: ignore[override]
		d = OriginItem.to_dict(self)
		d.update({"imageId": self.imageId, "caption": self.caption})
		return d


OriginItems = Union[OriginParagraph, OriginFigure]


@dataclass(slots=True)
class OriginData:
	id: str
	items: List[OriginItems] = field(default_factory=list)

	def to_dict(self) -> dict:
		return {
			"id": self.id,
			# Represent items as a list; xmltodict will create repeated <items>
			"items": [item.to_dict() for item in self.items],
		}

	@staticmethod
	def from_dict(d: dict) -> "OriginData":
		if "id" not in d:
			raise ValueError("Missing 'id' field in data root")
		raw_items = d.get("items", [])
		# xmltodict returns a dict if only one, list if multiple
		if isinstance(raw_items, dict):
			raw_items_list = [raw_items]
		else:
			raw_items_list = list(raw_items)
		items = [OriginItem.from_dict(it) for it in raw_items_list]
		return OriginData(id=str(d["id"]), items=items)


def origin2xml(data: OriginData, pretty: bool = True) -> str:
	"""Serialize OriginData to XML using xmltodict for simplicity."""
	obj = {"data": data.to_dict()}
	xml = xmltodict.unparse(obj, pretty=pretty, full_document=True, encoding="utf-8")
	# xmltodict.unparse returns bytes if encoding specified
	if isinstance(xml, bytes):
		return xml.decode("utf-8")
	return xml


def xml2origin(xml: str) -> OriginData:
	"""Parse XML produced by origin2xml back into OriginData."""
	parsed = xmltodict.parse(xml)
	if "data" not in parsed:
		raise ValueError("XML root must contain <data>")
	return OriginData.from_dict(parsed["data"])
