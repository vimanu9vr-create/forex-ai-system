"""AWS integration routes — S3 durable artifact storage (boto3)."""

from fastapi import APIRouter

from app.services import aws_s3
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
