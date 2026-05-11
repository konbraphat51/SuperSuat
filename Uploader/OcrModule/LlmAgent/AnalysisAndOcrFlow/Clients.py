import boto3  # type: ignore[import]
from langchain_aws import ChatBedrockConverse

BEDROCK_CLIENT = boto3.client("bedrock-runtime", region_name="ap-northeast-1")   # type: ignore[no-untyped-call]
ANALYST_VLM = ChatBedrockConverse(
    model="global.anthropic.claude-sonnet-4-6",
    temperature=1,
    client=BEDROCK_CLIENT,
)
PAGE_CHECKER_LLM = ChatBedrockConverse(
    model="global.anthropic.claude-haiku-4-5-20251001-v1:0",
    temperature=1,
    client=BEDROCK_CLIENT,
)
