import boto3  # type: ignore[import]
from langchain_aws import ChatBedrockConverse

BEDROCK_CLIENT = boto3.client("bedrock-runtime", region_name="us-east-1")   # type: ignore[no-untyped-call]
ANALYST_VLM = ChatBedrockConverse(
    model="anthropic.claude-3-5-sonnet-20241022-v2:0",
    temperature=0,
    client=BEDROCK_CLIENT,
)
