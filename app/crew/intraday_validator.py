"""
intraday_validator — on-demand CrewAI verdict on ONE 15m liquidity-sweep signal.

The intraday_engine produces the setup deterministically; this asks a 20-year ICT
desk persona "would I take THIS with my own capital?" It is ON-DEMAND (a button /
endpoint), NOT run on every scan, so we don't fire an LLM call per pair per poll.

Falls back to a deterministic rule-based verdict when the LLM/crew is unavailable
(no key, network error), so the endpoint never hard-fails.
"""

import ast
import json
import re

from crewai import Agent, Task, Crew

from app.config import OPENAI_API_KEY, LLM_PROVIDER
from app.crew.llm import get_crew_llm

_validator_agent = Agent(
    role="Proprietary FX Desk Trader — Intraday Liquidity (ICT / SMC)",
    goal=("Judge whether a SPECIFIC 15m liquidity-sweep setup is worth real risk, or "
          "should be skipped. Be ruthless — most setups are skips."),
    backstory=("You spent 20 years trading intraday liquidity raids in the London and "
               "New York killzones. You only take a sweep-reversal when the stop hunt, "
               "the displacement that breaks structure (MSS), and the FVG/OTE entry all "
               "line up IN-SESSION at >= 1:2, targeting clean opposite liquidity. You "
               "pass on anything mid-range or out-of-session, and you never invent "
               "numbers — you judge only the levels you are given."),
    verbose=False,
    max_iter=2,
    llm=get_crew_llm(),   # Bedrock when LLM_PROVIDER=bedrock, else CrewAI default (OpenAI)
)


def _task(sig: dict) -> Task:
    # Bake the signal into the description (Python f-string) and call kickoff() with
    # NO inputs, so CrewAI does not try to .format() the literal JSON in expected_output.
    desc = (
        "Evaluate THIS 15m sweep-reversal setup. Do NOT invent new numbers — judge only these:\n"
        f"  Pair:            {sig.get('pair')}\n"
        f"  Direction:       {sig.get('signal')}\n"
        f"  Entry:           {sig.get('entry')}  (basis: {sig.get('entry_basis')})\n"
        f"  Stop loss:       {sig.get('stop_loss')}\n"
        f"  Take profit:     {sig.get('take_profit')}\n"
        f"  Risk:Reward:     {sig.get('risk_reward')}\n"
        f"  Swept liquidity: {sig.get('swept_liquidity')}\n"
        f"  MSS level:       {sig.get('mss_level')}\n"
        f"  Killzone:        {sig.get('killzone')}\n"
        f"  Engine quality:  {sig.get('quality_score')}/100\n\n"
        "Decide TAKE or SKIP. A TAKE requires ALL of: an in-session (London/NY) sweep, "
        "displacement that broke structure (MSS), entry at an FVG/OTE retracement, and "
        ">= 1:2 R:R with the target at clean opposite liquidity. If anything is mid-range, "
        "out-of-session, or the target is not at real liquidity, SKIP."
    )
    expected = (
        'Output a one-line JSON FIRST: '
        '{"verdict": "TAKE", "confidence": 72, "reason": "<one sentence>"} '
        '(verdict is "TAKE" or "SKIP", confidence 0-100). '
        "Then 2-3 sentences of desk reasoning ending with: "
        "Would I take this with my own capital?"
    )
    return Task(description=desc, expected_output=expected, agent=_validator_agent)


def _to_text(result) -> str:
    for attr in ("raw", "result", "output"):
        value = getattr(result, attr, None)
        if isinstance(value, str) and value.strip():
            return value
    return str(result)


def _parse_verdict(text: str) -> dict:
    for m in re.finditer(r"\{.*?\}", text, flags=re.DOTALL):
        for parser in (json.loads, ast.literal_eval):
            try:
                data = parser(m.group(0))
                if isinstance(data, dict) and "verdict" in data:
                    return {
                        "verdict": str(data.get("verdict", "")).upper(),
                        "confidence": int(float(data.get("confidence", 0) or 0)),
                        "reason": str(data.get("reason", "")).strip(),
                    }
            except Exception:
                continue
    # Couldn't parse JSON — infer verdict from the prose
    upper = text.upper()
    verdict = "TAKE" if ("TAKE" in upper and "SKIP" not in upper) else "SKIP"
    return {"verdict": verdict, "confidence": 0, "reason": text.strip()[:200]}


def _rule_based(sig: dict) -> dict:
    try:
        rr = float(sig.get("risk_reward") or 0)
    except (TypeError, ValueError):
        rr = 0.0
    kz = sig.get("killzone") or ""
    in_kz = kz in ("London Open", "New York Open")
    take = in_kz and rr >= 2.0
    bits = [f"{'in' if in_kz else 'out-of'}-session ({kz or 'none'})",
            f"R:R {rr:.1f}",
            "FVG entry" if sig.get("entry_basis") == "FVG" else "OTE entry"]
    return {
        "verdict": "TAKE" if take else "SKIP",
        "confidence": int(sig.get("quality_score", 60 if take else 40)),
        "reason": ", ".join(bits),
        "source": "rule_based_fallback",
        "raw": "LLM crew unavailable — deterministic checklist verdict.",
    }


def validate_intraday_signal(sig: dict) -> dict:
    """Return {verdict, confidence, reason, source, raw}. Never raises."""
    if not sig:
        return {"verdict": "SKIP", "confidence": 0, "reason": "no signal provided",
                "source": "rule_based_fallback", "raw": ""}
    if LLM_PROVIDER != "bedrock" and not OPENAI_API_KEY:
        return _rule_based(sig)   # no LLM configured (neither Bedrock nor OpenAI)
    try:
        crew = Crew(agents=[_validator_agent], tasks=[_task(sig)], verbose=False, tracing=False)
        raw = _to_text(crew.kickoff())
        out = _parse_verdict(raw)
        out["raw"] = raw
        out["source"] = "crew"
        return out
    except Exception as e:
        fallback = _rule_based(sig)
        fallback["warning"] = f"crew failed: {e}"
        return fallback
