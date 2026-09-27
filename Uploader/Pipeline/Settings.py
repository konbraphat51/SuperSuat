"""What the OCR and the Leveler run with, as stored beside what they produced."""

from dataclasses import asdict, dataclass, fields
from typing import Any, Literal, Self, get_args

from OcrModule.MdWriter.FigureCorrector.FigureCorrectionTool import (
    DEFAULT_MAX_CALL_COUNT,
)
from Pipeline.ChatModels import Provider

Detector = Literal["doclayout", "yomitoku", "ppstructure"]
"""The layout model that finds the figures of each page."""

DETECTORS: tuple[Detector, ...] = get_args(Detector)
"""Every figure detector, for a command line to choose from."""

Reference = Literal["none", "yomitoku"]
"""The local OCR whose text the model checks its characters against, if any."""

REFERENCES: tuple[Reference, ...] = get_args(Reference)
"""Every reference reader, for a command line to choose from."""


@dataclass(frozen=True)
class _Settings:
    """Settings stored as a JSON object of their fields."""

    def to_dict(self) -> dict[str, Any]:
        """The settings as plain JSON values."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Settings read back from to_dict(); a field it lacks takes its
        default, and a key no longer a field is left out."""
        names = {field.name for field in fields(cls)}
        return cls(**{key: value for key, value in data.items() if key in names})


@dataclass(frozen=True)
class OcrSettings(_Settings):
    """What the MdWriter OCR runs with."""

    provider: Provider = "openai"
    model: str = "gpt-5.6-luna"  # writes the pages, and settles the page turns
    reasoning_effort: str | None = None  # None leaves the model's default
    max_tokens: int = 16000  # one answer carries one page, with room to reason
    detector: Detector = "doclayout"
    reference: Reference = "none"
    # the Bedrock model redrawing figure boxes found wrong; None leaves the tool out
    figure_corrector_model: str | None = "qwen.qwen3-vl-235b-a22b"
    max_figure_corrections: int = DEFAULT_MAX_CALL_COUNT  # per page
    dpi: int = 200  # the page indexes and figure boxes of the result refer to it
    max_parallel: int = 8  # most pages sent to the model at once
    max_pages: int | None = None  # read only the first pages; None for all


@dataclass(frozen=True)
class LevelSettings(_Settings):
    """What the Leveler runs with."""

    provider: Provider = "openai"
    model: str = "gpt-6-sol"
    reasoning_effort: str | None = None  # None leaves the model's default
    max_tokens: int = 16000
