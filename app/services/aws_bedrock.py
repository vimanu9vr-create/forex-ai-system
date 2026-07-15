"""
aws_bedrock — Amazon Bedrock (Claude) via boto3.

A self-contained boto3 `bedrock-runtime` completion (the Converse API), exposed at
/aws/bedrock/ask, plus a status probe. Complements the CrewAI-agent Bedrock path
(crew/llm.py, selected by LLM_PROVIDER=bedrock). Standard AWS credential chain (env vars /
IAM task role — no keys in code). Graceful no-op with a reason when unconfigured.
"""

import threading

from app.config import BEDROCK_MODEL_ID, BEDROCK_REGION, LLM_PROVIDER

_client = None            # None = untried; False = tried & unavailable; else a boto3 client
_lock = threading.Lock()


def _runtime():
    global _client
    if _client is not None:
        return _client or None
    with _lock:
        if _client is None:
            try:
                import boto3
                _client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION or None)
            except Exception as e:
                print(f"[aws_bedrock] bedrock-runtime unavailable: {e}")
                _client = False
    return _client or None


def is_available() -> bool:
    return _runtime() is not None


def chat(prompt: str, system: str = None, max_tokens: int = 512) -> dict:
    """One-shot completion via the Bedrock Converse API. {ok, text, model} or {ok:False, error}."""
    c = _runtime()
    if not c:
        return {"ok": False, "error": "Bedrock not available (boto3 / credentials / region not set)"}
    try:
        kwargs = {
            "modelId": BEDROCK_MODEL_ID,
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": 0.2},
        }
        if system:
            kwargs["system"] = [{"text": system}]
        resp = c.converse(**kwargs)
        text = resp["output"]["message"]["content"][0]["text"]
        return {"ok": True, "text": text, "model": BEDROCK_MODEL_ID}
    except Exception as e:
        return {"ok": False, "error": str(e), "model": BEDROCK_MODEL_ID}


def status() -> dict:
    """For /aws/bedrock/status — never raises."""
    return {
        "provider_selected": LLM_PROVIDER,
        "bedrock_available": is_available(),
        "model_id": BEDROCK_MODEL_ID,
        "region": BEDROCK_REGION,
        "credential_chain": "env vars / shared config / IAM task role (ECS/EC2)",
        "note": "Set LLM_PROVIDER=bedrock + AWS credentials to route the CrewAI agents through Bedrock.",
    }
