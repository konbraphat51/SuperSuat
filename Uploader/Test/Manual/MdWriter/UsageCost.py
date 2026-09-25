"""Adding up the tokens every request of a run used, and what they cost, page by page."""

import threading
from dataclasses import dataclass
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
    """The tokens every request for one page used, retries included.

    Attributes:
        kind: Whether the page was written or filled.
        requests: How many requests the page took.
        input_tokens: Every input token, cached ones included.
        cached_tokens: Input tokens read from the cache.
        cache_write_tokens: Input tokens written to the cache.
        output_tokens: Every output token, reasoning included.
        reasoning_tokens: Output tokens spent on reasoning.
    """

    kind: str
    requests: int = 0
    input_tokens: int = 0
    cached_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0

    def add(self, usage: dict[str, Any]) -> None:
        """Counts one more request's usage in."""
        input_details = usage.get("input_token_details") or {}
        output_details = usage.get("output_token_details") or {}

        self.requests += 1
        self.input_tokens += usage.get("input_tokens", 0)
        self.cached_tokens += input_details.get("cache_read", 0) or 0
        self.cache_write_tokens += input_details.get("cache_creation", 0) or 0
        self.output_tokens += usage.get("output_tokens", 0)
        self.reasoning_tokens += output_details.get("reasoning", 0) or 0

    def cost(self, pricing: Pricing) -> float:
        """What these tokens cost at the given prices, in USD."""
        uncached = self.input_tokens - self.cached_tokens - self.cache_write_tokens
        return (
            uncached * pricing.input
            + self.cached_tokens * pricing.cached_input
            + self.cache_write_tokens * pricing.cache_write
            + self.output_tokens * pricing.output
        ) / TOKENS_PER_PRICE


class UsageRecorder(BaseCallbackHandler):
    """Records the usage of every chat model request, by the page it was for.

    PageTranscriber puts the page's index and kind in each request's
    metadata, which is how a request is told apart from the others running
    at the same time."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._request_pages: dict[UUID, tuple[int, str]] = {}
        self.pages: dict[int, PageUsage] = {}

    def reset(self) -> None:
        """Forgets every page, for the next document."""
        with self._lock:
            self._request_pages.clear()
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
        """Notes which page a request is for."""
        metadata = metadata or {}
        if "page_index" in metadata:
            with self._lock:
                self._request_pages[run_id] = (
                    metadata["page_index"],
                    metadata.get("page_kind", "?"),
                )

    def on_llm_end(self, response: LLMResult, *, run_id: UUID, **kwargs: Any) -> None:
        """Counts a finished request's usage in for its page."""
        with self._lock:
            page = self._request_pages.pop(run_id, None)
            if page is None:
                return

            for generations in response.generations:
                for generation in generations:
                    if not isinstance(generation, ChatGeneration):
                        continue
                    message = generation.message
                    if isinstance(message, AIMessage) and message.usage_metadata:
                        page_index, kind = page
                        self.pages.setdefault(page_index, PageUsage(kind)).add(
                            dict(message.usage_metadata)
                        )


def format_report(pages: dict[int, PageUsage], pricing: Pricing | None) -> str:
    """A table of every page's tokens and cost, with the totals under it."""
    header = f"{'page':>4} {'kind':<5} {'req':>3} {'input':>7} {'cached':>7} {'output':>7} {'reason':>7} {'USD':>9}"
    lines = [header, "-" * len(header)]
    total = PageUsage(kind="all")

    for page_index in sorted(pages):
        usage = pages[page_index]
        lines.append(_row(str(page_index), usage, pricing))
        total.requests += usage.requests
        total.input_tokens += usage.input_tokens
        total.cached_tokens += usage.cached_tokens
        total.cache_write_tokens += usage.cache_write_tokens
        total.output_tokens += usage.output_tokens
        total.reasoning_tokens += usage.reasoning_tokens

    lines.append("-" * len(header))
    lines.append(_row("all", total, pricing))

    if pricing is not None and pages:
        lines.append(f"per page: ${total.cost(pricing) / len(pages):.5f}")

    return "\n".join(lines)


def _row(label: str, usage: PageUsage, pricing: Pricing | None) -> str:
    """One line of the table."""
    cost = f"{usage.cost(pricing):.5f}" if pricing is not None else "-"
    return (
        f"{label:>4} {usage.kind:<5} {usage.requests:>3} {usage.input_tokens:>7} "
        f"{usage.cached_tokens:>7} {usage.output_tokens:>7} "
        f"{usage.reasoning_tokens:>7} {cost:>9}"
    )
