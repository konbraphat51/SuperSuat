"""Building the chat models the pipelines run on, on the OpenAI API or Amazon Bedrock."""

import os
from collections.abc import Sequence
from typing import Literal, get_args

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import BaseChatModel
from pydantic import SecretStr

Provider = Literal["openai", "bedrock"]
"""Where a chat model runs."""

PROVIDERS: tuple[Provider, ...] = get_args(Provider)
"""Every provider, for a command line to choose from."""

DEFAULT_REGION = "us-west-2"
"""The Bedrock region used when AWS_REGION and AWS_DEFAULT_REGION are both unset."""


def build_chat_model(
    provider: Provider,
    model_id: str,
    max_tokens: int,
    reasoning_effort: str | None = None,
    region: str | None = None,
    callbacks: Sequence[BaseCallbackHandler] = (),
) -> BaseChatModel:
    """A chat model of the given provider. The provider's package is imported
    only now, so that a command line runs without the one it does not use.

    Args:
        provider: Where the model runs.
        model_id: The provider's id of the model.
        max_tokens: Most tokens one answer may take.
        reasoning_effort: How hard an OpenAI reasoning model thinks, such as
            "low"; None leaves the model's default. Bedrock ignores it.
        region: The Bedrock region; None reads it from the environment.
        callbacks: Told of every request, such as to count its usage.
    """
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model_id,
            use_responses_api=True,
            max_tokens=max_tokens,  # type: ignore[call-arg]
            callbacks=list(callbacks),
            reasoning_effort=reasoning_effort,
        )

    return _build_bedrock_model(model_id, max_tokens, region, callbacks)


def _build_bedrock_model(
    model_id: str,
    max_tokens: int,
    region: str | None,
    callbacks: Sequence[BaseCallbackHandler],
) -> BaseChatModel:
    """A Bedrock chat model, on the short-term API key if one is set."""
    from langchain_aws import ChatBedrockConverse

    api_key = os.getenv("AWS_BEDROCK_SHORT_API_KEY") or os.getenv(
        "AWS_BEARER_TOKEN_BEDROCK"
    )
    if api_key:
        # bearer-token auth never reads the AWS profile, which may be broken locally
        os.environ["AWS_CONFIG_FILE"] = os.devnull
        os.environ.pop("AWS_PROFILE", None)

    return ChatBedrockConverse(
        model=model_id,
        region_name=region
        or os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or DEFAULT_REGION,
        max_tokens=max_tokens,
        temperature=0,
        callbacks=list(callbacks),
        api_key=SecretStr(api_key) if api_key else None,
    )
