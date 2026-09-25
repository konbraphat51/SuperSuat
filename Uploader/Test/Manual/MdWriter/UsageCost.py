"""Adding up the tokens every request of a run used, and what they cost, page by page."""

import threading
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, LLMResult


@dataclass(frozen=True)
class Pricing:
    """What a model charges, in USD per million tokens.

    Attributes:
        input: Input tokens not read from the cache.
        cached_input: Input tokens read from the cache.
        cache_write: Input tokens written to the cache.
        output: Output tokens, reasoning included.
    """

    input: float
    cached_input: float
    cache_write: float
    output: float


# The published prices of the models this test is run with.
PRICING = {
    "gpt-6-luna": Pricing(
        input=0.10, cached_input=0.01, cache_write=0.125, output=0.50
    ),
    "gpt-6-sol": Pricing(input=2.00, cached_input=0.20, cache_write=2.50, output=10.00),
}

# Tokens a price is quoted per.
TOKENS_PER_PRICE = 1_000_000


@dataclass
class PageUsage:
    """The tokens every request for one page used, retries and joins included.

    Attributes:
        requests: How many requests the page took.
        models: The models those requests went to.
        input_tokens: Every input token, cached ones included.
        cached_tokens: Input tokens read from the cache.
        cache_write_tokens: Input tokens written to the cache.
        output_tokens: Every output token, reasoning included.
        reasoning_tokens: Output tokens spent on reasoning.
        cost: What the requests cost in USD, each at its own model's prices,
            or None if a model is missing from PRICING.
    """

    requests: int = 0
    models: set[str] = field(default_factory=set)
    input_tokens: int = 0
    cached_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    cost: float | None = 0.0

    def add(self, model: str, usage: dict[str, Any]) -> None:
        """Counts one more request's usage in, priced as its model charges."""
        input_details = usage.get("input_token_details") or {}
        output_details = usage.get("output_token_details") or {}

        input_tokens = usage.get("input_tokens", 0)
        cached = input_details.get("cache_read", 0) or 0
        cache_write = input_details.get("cache_creation", 0) or 0
        output_tokens = usage.get("output_tokens", 0)

        self.requests += 1
        self.models.add(model)
        self.input_tokens += input_tokens
        self.cached_tokens += cached
        self.cache_write_tokens += cache_write
        self.output_tokens += output_tokens
        self.reasoning_tokens += output_details.get("reasoning", 0) or 0

        pricing = PRICING.get(model)
        if pricing is None or self.cost is None:
            self.cost = None
            return

        self.cost += (
            (input_tokens - cached - cache_write) * pricing.input
            + cached * pricing.cached_input
            + cache_write * pricing.cache_write
            + output_tokens * pricing.output
        ) / TOKENS_PER_PRICE

    def merge(self, other: "PageUsage") -> None:
        """Counts another page's usage in, for the totals."""
        self.requests += other.requests
        self.models |= other.models
        self.input_tokens += other.input_tokens
        self.cached_tokens += other.cached_tokens
        self.cache_write_tokens += other.cache_write_tokens
        self.output_tokens += other.output_tokens
        self.reasoning_tokens += other.reasoning_tokens
        self.cost = (
            None if self.cost is None or other.cost is None else self.cost + other.cost
        )


class UsageRecorder(BaseCallbackHandler):
    """Records the usage of every chat model request, by the page it was for.

    MdWriter puts the page's index in each request's metadata, which is how a
    request is told apart from the others running at the same time."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: dict[UUID, tuple[int, str]] = {}
        self.pages: dict[int, PageUsage] = {}

    def reset(self) -> None:
        """Forgets every page, for the next document."""
        with self._lock:
            self._requests.clear()
            self.pages = {}

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Notes which page a request is for, and which model it goes to."""
        metadata = metadata or {}
        params = kwargs.get("invocation_params") or {}
        model = str(params.get("model") or params.get("model_name") or "?")

        if "page_index" in metadata:
            with self._lock:
                self._requests[run_id] = (metadata["page_index"], model)

    def on_llm_end(self, response: LLMResult, *, run_id: UUID, **kwargs: Any) -> None:
        """Counts a finished request's usage in for its page."""
        with self._lock:
            request = self._requests.pop(run_id, None)
            if request is None:
                return

            page_index, model = request
            for generations in response.generations:
                for generation in generations:
                    if not isinstance(generation, ChatGeneration):
                        continue
                    message = generation.message
                    if isinstance(message, AIMessage) and message.usage_metadata:
                        self.pages.setdefault(page_index, PageUsage()).add(
                            model, dict(message.usage_metadata)
                        )


def format_report(pages: dict[int, PageUsage]) -> str:
    """A table of every page's tokens and cost, with the totals under it."""
    header = (
        f"{'page':>4} {'req':>3} {'input':>7} {'cached':>7} {'output':>7} "
        f"{'reason':>7} {'USD':>9}  models"
    )
    lines = [header, "-" * len(header)]
    total = PageUsage()

    for page_index in sorted(pages):
        lines.append(_row(str(page_index), pages[page_index]))
        total.merge(pages[page_index])

    lines.append("-" * len(header))
    lines.append(_row("all", total))

    if total.cost is not None and pages:
        lines.append(f"per page: ${total.cost / len(pages):.5f}")

    return "\n".join(lines)


def _row(label: str, usage: PageUsage) -> str:
    """One line of the table."""
    cost = f"{usage.cost:.5f}" if usage.cost is not None else "-"
    return (
        f"{label:>4} {usage.requests:>3} {usage.input_tokens:>7} "
        f"{usage.cached_tokens:>7} {usage.output_tokens:>7} "
        f"{usage.reasoning_tokens:>7} {cost:>9}  {'+'.join(sorted(usage.models))}"
    )
