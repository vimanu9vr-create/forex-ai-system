"""
crew/llm — LLM factory for the CrewAI agents.

Returns a Bedrock-backed CrewAI LLM when LLM_PROVIDER=bedrock, else None so the agents fall
back to CrewAI's default (OpenAI). Opt-in via env — default behaviour is unchanged, and if
the Bedrock LLM can't be constructed it degrades to the default rather than crashing.
"""

from app.config import LLM_PROVIDER, BEDROCK_MODEL_ID, BEDROCK_REGION


def get_crew_llm():
    """A CrewAI LLM for Bedrock, or None (= use the default OpenAI LLM)."""
    if LLM_PROVIDER != "bedrock":
        return None
    try:
        from crewai import LLM
        # CrewAI/litellm route Bedrock via the "bedrock/<model-id>" prefix + the AWS cred chain.
        return LLM(model=f"bedrock/{BEDROCK_MODEL_ID}", aws_region_name=BEDROCK_REGION)
    except Exception as e:
        print(f"[crew.llm] Bedrock LLM init failed ({e}); falling back to default OpenAI")
        return None
