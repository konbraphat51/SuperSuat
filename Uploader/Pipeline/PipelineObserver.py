"""What a pipeline run tells of how it goes."""

from typing import Protocol


class PipelineObserver(Protocol):
    """Told of how a pipeline run goes, such as to show it to a person."""

    def step(self, name: str) -> None:
        """A step of the run has started, such as "rendering"."""
        ...

    def progress(self, label: str, done: int, total: int) -> None:
        """A labelled stage of the run, such as "writing", has done `done` of its `total` items."""
        ...


class SilentObserver:
    """Told of a run, and tells no one."""

    def step(self, name: str) -> None:
        """Ignores the step."""

    def progress(self, label: str, done: int, total: int) -> None:
        """Ignores the progress."""
