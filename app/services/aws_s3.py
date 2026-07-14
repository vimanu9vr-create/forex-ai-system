"""
aws_s3 — durable artifact storage on Amazon S3 (boto3).

The intraday forward-test log and backtest results live locally on the Docker volume / ECS
task disk, which is lost when the container is replaced. This module mirrors them to an S3
bucket so the paper-trading track record is durable. It uses the standard AWS credential
chain (env vars locally, or an IAM task role on ECS/EC2 — no keys in code).

Every function is a graceful no-op with a logged reason when AWS_S3_BUCKET / boto3 / creds are
absent, so the app behaves identically with or without AWS configured.
"""

import json
import threading

from app.config import AWS_S3_BUCKET, AWS_REGION

_client = None            # None = not yet tried; False = tried & unavailable; else a boto3 client
_lock = threading.Lock()


def _s3():
    global _client
    if _client is not None:
        return _client or None
    with _lock:
        if _client is None:
            try:
                import boto3
                _client = boto3.client("s3", region_name=AWS_REGION or None)
            except Exception as e:
                print(f"[aws_s3] boto3/S3 client unavailable: {e}")
                _client = False
    return _client or None


def is_configured() -> bool:
    return bool(AWS_S3_BUCKET) and _s3() is not None


def upload_file(local_path: str, key: str) -> bool:
    """Upload a local file to s3://AWS_S3_BUCKET/key. No-op (False) if AWS isn't configured."""
    if not AWS_S3_BUCKET:
        return False
    c = _s3()
    if not c:
        return False
    try:
        c.upload_file(local_path, AWS_S3_BUCKET, key)
        print(f"[aws_s3] uploaded {local_path} -> s3://{AWS_S3_BUCKET}/{key}")
        return True
    except Exception as e:
        print(f"[aws_s3] upload_file failed ({key}): {e}")
        return False


def upload_json(obj, key: str) -> bool:
    """Serialize obj to JSON and put it at s3://AWS_S3_BUCKET/key."""
    if not AWS_S3_BUCKET:
        return False
    c = _s3()
    if not c:
        return False
    try:
        c.put_object(Bucket=AWS_S3_BUCKET, Key=key,
                     Body=json.dumps(obj, indent=2, default=str).encode(),
                     ContentType="application/json")
        print(f"[aws_s3] put s3://{AWS_S3_BUCKET}/{key}")
        return True
    except Exception as e:
        print(f"[aws_s3] upload_json failed ({key}): {e}")
        return False


def status() -> dict:
    """For the /aws/status endpoint — never raises."""
    return {
        "configured": is_configured(),
        "bucket": AWS_S3_BUCKET or None,
        "region": AWS_REGION or None,
        "boto3_available": _s3() is not None,
        "credential_chain": "env vars / shared config / IAM task role (ECS/EC2)",
        "note": "Set AWS_S3_BUCKET + AWS credentials to enable; no-ops gracefully otherwise.",
    }
