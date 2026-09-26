"""A chat model that answers from a script and records what it was sent."""

from collections.abc import Sequence
from typing import Any

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatResult


class RecordingFakeModel(GenericFakeChatModel):
    """Answers with the given replies in turn, keeping every request it got,
    and the tools it was bound to."""

    requests: list[list[BaseMessage]] = []
    tools: list[Any] = []

    @classmethod
    def replying(cls, *replies: str | AIMessage) -> "RecordingFakeModel":
        return cls(
            messages=iter(
                [
                    reply if isinstance(reply, AIMessage) else AIMessage(content=reply)
                    for reply in replies
                ]
            ),
            requests=[],
            tools=[],
        )

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> "RecordingFakeModel":
        self.tools = list(tools)
        return self

    def _generate(
        self, messages: list[BaseMessage], *args: Any, **kwargs: Any
    ) -> ChatResult:
        # a copy: the caller keeps appending to the same list between attempts
        self.requests.append(list(messages))
        return super()._generate(messages, *args, **kwargs)
