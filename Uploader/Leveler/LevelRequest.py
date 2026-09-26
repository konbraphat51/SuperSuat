"""Asking the leveler model for heading levels until every heading asked about has one."""

import logging
from typing import Any, TypeVar

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.runnables import Runnable

from .Headings import Heading, apply_levels, retry_message
from .LevelerSchema import HeadingLevels, SkeletonLevels

logger = logging.getLogger(__name__)

# Guard against a model that keeps leaving headings unanswered.
MAX_ATTEMPT_COUNT = 3

# The structured answers a leveling request can be made for.
AnswerT = TypeVar("AnswerT", HeadingLevels, SkeletonLevels)


def request_levels(
    model: Runnable[Any, Any],
    answer_type: type[AnswerT],
    messages: list[BaseMessage],
    headings: list[Heading],
    levels: dict[int, float],
    label: str,
) -> list[AnswerT]:
    """Records a level for every heading into `levels`, asking again about
    what an answer left out, and returns every answer the model gave.

    Args:
        model: The chat model, already bound to `answer_type`.
        answer_type: The structured answer the model gives.
        messages: The request; the answers and the retries are appended to it.
        headings: The headings the model is asked about.
        levels: Where the levels are recorded, keyed by block_index.
        label: What the request is, for the log.

    Raises:
        RuntimeError: A heading was still left without a level after
            MAX_ATTEMPT_COUNT attempts.
    """
    answers: list[AnswerT] = []

    for attempt in range(1, MAX_ATTEMPT_COUNT + 1):
        answer = model.invoke(messages)
        if not isinstance(answer, answer_type):
            raise RuntimeError("The leveler model returned no heading levels.")

        logger.info(
            "Leveler | %s attempt %d: %d level(s)", label, attempt, len(answer.levels)
        )
        messages.append(AIMessage(content=answer.model_dump_json()))
        answers.append(answer)

        problems = apply_levels(answer.levels, headings, levels)
        unleveled = [h for h in headings if h.block_index not in levels]

        if not problems and not unleveled:
            return answers

        logger.warning(
            "Leveler | %s attempt %d left %d heading(s) unleveled",
            label,
            attempt,
            len(unleveled),
        )
        messages.append(HumanMessage(content=retry_message(problems, unleveled)))

    unleveled_count = len([h for h in headings if h.block_index not in levels])
    raise RuntimeError(
        f"{unleveled_count} heading(s) were left without a level after "
        f"{MAX_ATTEMPT_COUNT} attempts."
    )
