"""AWS integration routes — S3 durable artifact storage (boto3)."""

from fastapi import APIRouter, Body

from app.services import aws_s3, aws_bedrock
from app.services.intraday_forward_test import backup_to_s3

router = APIRouter()


@router.get("/aws/status")
def aws_status():
    """S3 integration status — configured bucket/region + whether boto3/credentials resolve."""
    return aws_s3.status()


@router.post("/aws/backup")
def aws_backup():
    """Persist the intraday forward-test log + a stats snapshot to S3 (durable storage that
    survives container/task replacement). No-ops with a clear reason if AWS isn't configured."""
    return backup_to_s3()


@router.get("/aws/bedrock/status")
def bedrock_status():
    """Amazon Bedrock status — selected LLM provider, model id, region, and availability."""
    return aws_bedrock.status()


@router.post("/aws/bedrock/ask")
def bedrock_ask(body: dict = Body(default={})):
    """Direct Bedrock (Claude) completion via boto3 Converse — health/demo of the Bedrock path.
    No-ops with a clear reason if Bedrock/credentials aren't configured."""
    prompt = (body or {}).get("prompt") or "Reply with one short sentence confirming Bedrock works."
    return aws_bedrock.chat(prompt)
