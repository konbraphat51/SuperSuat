import boto3  # type: ignore[import]
from langchain_aws import ChatBedrockConverse

BEDROCK_CLIENT = boto3.client("bedrock-runtime", region_name="ap-northeast-1")   # type: ignore[no-untyped-call]
ANALYST_VLM = ChatBedrockConverse(
    model="jp.anthropic.claude-sonnet-4-6",
    temperature=1,
    client=BEDROCK_CLIENT,
    additional_model_request_fields={
        "thinking": {
            "type": "enabled",
            "budget_tokens": 2048
        }
    }
)
