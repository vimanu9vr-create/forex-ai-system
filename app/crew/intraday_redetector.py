"""
intraday_redetector — an INDEPENDENT second opinion on the 15m liquidity sweep.

Different from `intraday_validator`: the validator is handed the engine's finished
signal and only rules TAKE/SKIP on those exact numbers (it cannot disagree on what the
setup IS). This module instead pulls the candles itself, runs the SMC detectors to build
a structural EVIDENCE packet (swings, equal-highs/lows, recent sweeps, FVGs, killzone,
HTF bias) WITHOUT the engine's signal, and asks a desk-trader agent to form its OWN read:
is there a take-able sweep-reversal right now, which way, and at what levels — CONFIRM or
REJECT. Then we compare that independent read to the engine's signal (agree / disagree).

LLM path when OPENAI_API_KEY is set; otherwise a deterministic INDEPENDENT fallback that
re-detects with STRICTER quality filters (engineered pools only + real-raid depth), which
can legitimately reject a setup the lenient live engine took. Never raises.
"""

import ast
import json
import re

from app.config import OPENAI_API_KEY, INTRADAY_MIN_RR, LLM_PROVIDER
from app.crew.llm import get_crew_llm
from app.services.market_data import get_forex_intraday
from app.smart_money.structure import detect_swings
from app.smart_money.liquidity import detect_equal_highs, detect_equal_lows
from app.smart_money.sweeps import detect_buy_side_sweeps, detect_sell_side_sweeps
from app.smart_money.fvg import detect_fvg
from app.smart_money.killzones import in_killzone
from app.smart_money.intraday_engine import analyze_intraday, htf_bias_from

_SESSION_KZ = {"london": {"London Open"}, "newyork": {"New York Open"},
               "both": {"London Open", "New York Open"}}


def _round(p, pair):
    return round(p, 3 if "JPY" in pair.upper() else 5)


def build_evidence(pair: str, tf: str = "15min", session: str = "london") -> dict:
    """Pull candles + run detectors -> a compact structural evidence packet (NO engine signal)."""
    daily = get_forex_intraday(pair, interval="1day", outputsize=200)
    h4 = get_forex_intraday(pair, interval="4h", outputsize=200)
    candles = get_forex_intraday(pair, interval=tf, outputsize=500) or []
    bias, d_dir, h_dir = htf_bias_from(daily, h4)
    if len(candles) < 60:
        return {"pair": pair, "tf": tf, "error": "insufficient candles", "candles": len(candles)}

    swings = detect_swings(candles, lookback=2)
    sh, sl = swings["swing_highs"], swings["swing_lows"]
    eq_h, eq_l = detect_equal_highs(sh), detect_equal_lows(sl)
    sell_zones = list(eq_l) + [{"price": s["price"], "first_touch": s["timestamp"]} for s in sl]
    buy_zones = list(eq_h) + [{"price": s["price"], "first_touch": s["timestamp"]} for s in sh]
    sell_sweeps = detect_sell_side_sweeps(candles, sell_zones)   # -> long bias
    buy_sweeps = detect_buy_side_sweeps(candles, buy_zones)      # -> short bias

    last = candles[-1]
    kz = in_killzone(last["datetime"])
    return {
        "pair": pair, "tf": tf, "session": session,
        "htf_bias": bias, "htf_daily": d_dir, "htf_4h": h_dir,
        "current_killzone": kz.get("killzone"), "entry_allowed": kz.get("entry_allowed"),
        "last_price": _round(last["close"], pair), "last_time": last["datetime"],
        "swing_highs": [_round(s["price"], pair) for s in sh[-8:]],
        "swing_lows": [_round(s["price"], pair) for s in sl[-8:]],
        "equal_highs": [_round(e["price"], pair) for e in eq_h[-4:]],
        "equal_lows": [_round(e["price"], pair) for e in eq_l[-4:]],
        "recent_sell_side_sweeps": [{"price": _round(s["price"], pair), "time": s["timestamp"]} for s in sell_sweeps[-3:]],
        "recent_buy_side_sweeps": [{"price": _round(s["price"], pair), "time": s["timestamp"]} for s in buy_sweeps[-3:]],
        "recent_bullish_fvg": [[_round(f["start"], pair), _round(f["end"], pair)] for f in detect_fvg(candles)["bullish_fvg_zones"][-2:]],
        "recent_bearish_fvg": [[_round(f["start"], pair), _round(f["end"], pair)] for f in detect_fvg(candles)["bearish_fvg_zones"][-2:]],
        "_candles": candles,   # kept for the deterministic fallback; stripped before return
    }


def _agree(direction: str, engine_sig: dict) -> str:
    """Compare the independent read to the engine's signal."""
    if not engine_sig:
        return "no engine signal to compare"
    eng = (engine_sig.get("signal") or "").upper()
    ind = (direction or "").upper()
    if ind in ("NONE", "") or ind not in ("BUY", "SELL"):
        return f"DISAGREE — engine says {eng}, independent sees no setup"
    return f"AGREE on {eng}" if ind == eng else f"DISAGREE — engine {eng} vs independent {ind}"


def _parse(text: str) -> dict:
    for m in re.finditer(r"\{.*?\}", text, flags=re.DOTALL):
        for parser in (json.loads, ast.literal_eval):
            try:
                d = parser(m.group(0))
                if isinstance(d, dict) and "verdict" in d:
                    return d
            except Exception:
                continue
    return {}


def _deterministic(ev: dict, engine_sig: dict) -> dict:
    """INDEPENDENT fallback: re-detect with STRICTER filters than the live engine. If a
    setup still survives, CONFIRM (with the stricter read); else REJECT."""
    candles = ev.get("_candles") or []
    allowed = _SESSION_KZ.get(ev.get("session"), _SESSION_KZ["london"])
    strict = analyze_intraday(ev["pair"], candles, htf_bias=ev.get("htf_bias"), tf=ev.get("tf"),
                              allowed_killzones=allowed, equal_pools_only=True,
                              min_sweep_atr=0.3, min_disp_body_atr=0.3)
    if strict:
        direction = strict["signal"]
        return {
            "verdict": "CONFIRM", "direction": direction,
            "entry": strict["entry"], "stop_loss": strict["stop_loss"], "take_profit": strict["take_profit"],
            "confidence": min(int(strict.get("quality_score", 60)), 90),
            "reason": ("Independent strict re-detection (engineered pools + real-raid depth) "
                       f"finds the same {direction} sweep-reversal."),
            "agreement": _agree(direction, engine_sig),
            "source": "deterministic_strict",
        }
    return {
        "verdict": "REJECT", "direction": "NONE",
        "entry": None, "stop_loss": None, "take_profit": None, "confidence": 55,
        "reason": ("No setup survives the stricter independent criteria (needs an engineered "
                   "equal-high/low raid with real penetration + strong displacement)."),
        "agreement": _agree("NONE", engine_sig),
        "source": "deterministic_strict",
    }


def _llm(ev: dict, engine_sig: dict) -> dict:
    from crewai import Agent, Task, Crew
    agent = Agent(
        role="Independent Proprietary FX Desk Trader — Intraday Liquidity (ICT / SMC)",
        goal=("From the structure alone, decide INDEPENDENTLY whether there is a take-able 15m "
              "liquidity sweep-reversal right now, which direction, and at what levels. Be ruthless."),
        backstory=("20 years trading London/NY killzone liquidity raids. You form your own read "
                   "from the price structure — swept pools, displacement that breaks structure, and "
                   "an FVG/OTE entry into clean opposite liquidity at >= 1:2. You are NOT told anyone "
                   "else's trade; you judge only the evidence and you never invent levels not implied "
                   "by it. Most of the time the right call is REJECT."),
        verbose=False, max_iter=2,
        llm=get_crew_llm(),   # Bedrock when LLM_PROVIDER=bedrock, else CrewAI default (OpenAI)
    )
    desc = (
        "Structural evidence (you are NOT given any pre-made signal — form your own):\n"
        f"  Pair / TF:        {ev['pair']} / {ev['tf']}\n"
        f"  HTF bias:         {ev['htf_bias']} (Daily {ev['htf_daily']}, 4H {ev['htf_4h']})\n"
        f"  Current killzone: {ev['current_killzone']} (entry_allowed={ev['entry_allowed']})\n"
        f"  Last price:       {ev['last_price']}\n"
        f"  Swing highs:      {ev['swing_highs']}\n"
        f"  Swing lows:       {ev['swing_lows']}\n"
        f"  Equal highs (BSL):{ev['equal_highs']}\n"
        f"  Equal lows (SSL): {ev['equal_lows']}\n"
        f"  Sell-side sweeps: {ev['recent_sell_side_sweeps']}\n"
        f"  Buy-side sweeps:  {ev['recent_buy_side_sweeps']}\n"
        f"  Bullish FVGs:     {ev['recent_bullish_fvg']}\n"
        f"  Bearish FVGs:     {ev['recent_bearish_fvg']}\n\n"
        "A valid setup needs ALL of: an in-session (London/NY) sweep of resting liquidity, "
        "displacement that breaks the last opposing swing (MSS), an FVG/OTE entry, and >= 1:2 R:R "
        f"(min {INTRADAY_MIN_RR}) targeting clean opposite liquidity. Only trade WITH the HTF bias."
    )
    expected = (
        'One-line JSON FIRST: {"verdict":"CONFIRM"|"REJECT", "direction":"BUY"|"SELL"|"NONE", '
        '"entry":<num|null>, "stop_loss":<num|null>, "take_profit":<num|null>, "confidence":0-100, '
        '"reason":"<one sentence>"}. Then 2-3 sentences of desk reasoning ending with: '
        "Would I take this with my own capital?"
    )
    crew = Crew(agents=[agent], tasks=[Task(description=desc, expected_output=expected, agent=agent)],
                verbose=False, tracing=False)
    raw = crew.kickoff()
    text = getattr(raw, "raw", None) or str(raw)
    data = _parse(text)
    if not data:
        out = _deterministic(ev, engine_sig)
        out["warning"] = "LLM output unpar's-able — used deterministic fallback"
        out["raw"] = text
        return out
    direction = str(data.get("direction", "NONE")).upper()
    return {
        "verdict": str(data.get("verdict", "REJECT")).upper(),
        "direction": direction,
        "entry": data.get("entry"), "stop_loss": data.get("stop_loss"), "take_profit": data.get("take_profit"),
        "confidence": int(float(data.get("confidence", 0) or 0)),
        "reason": str(data.get("reason", "")).strip(),
        "agreement": _agree(direction, engine_sig),
        "source": "crew", "raw": text,
    }


def redetect_intraday(pair: str, tf: str = "15min", session: str = "london",
                      engine_sig: dict = None) -> dict:
    """Independent second opinion on `pair`. Returns {verdict, direction, entry/sl/tp,
    confidence, reason, agreement, source}. Never raises."""
    try:
        ev = build_evidence(pair, tf, session)
    except Exception as e:
        return {"verdict": "ERROR", "direction": "NONE", "reason": f"evidence build failed: {e}",
                "source": "error"}
    if ev.get("error"):
        return {"verdict": "ERROR", "direction": "NONE", "reason": ev["error"], "source": "error"}
    try:
        use_llm = LLM_PROVIDER == "bedrock" or OPENAI_API_KEY
        result = _llm(ev, engine_sig) if use_llm else _deterministic(ev, engine_sig)
    except Exception as e:
        result = _deterministic(ev, engine_sig)
        result["warning"] = f"crew failed: {e}"
    # Echo the structural context (minus the heavy candle array) for the UI.
    ev.pop("_candles", None)
    result["evidence"] = ev
    result["pair"] = pair
    return result
