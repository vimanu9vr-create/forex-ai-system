import ast
import json
import re

from fastapi import APIRouter

from app.agents.market_agent import MarketAgent
from app.crew.crew import trading_crew

router = APIRouter()
market_agent = MarketAgent()


def _to_text(result) -> str:
    for attr in ("raw", "result", "output"):
        value = getattr(result, attr, None)
        if isinstance(value, str) and value.strip():
            return value
    return str(result)


def _extract_signal(text: str) -> dict:
    """Extract structured signal from crew output text."""
    # Try JSON block first
    match = re.search(r"\{.*?\}", text, flags=re.DOTALL)
    if match:
        for parser in (json.loads, ast.literal_eval):
            try:
                data = parser(match.group(0))
                if isinstance(data, dict):
                    # Flatten nested trade_result if present
                    trade = data.get("trade_result") or data.get("trade") or data
                    return {
                        "pair":            trade.get("pair") or data.get("pair"),
                        "signal":          trade.get("signal") or data.get("signal"),
                        "entry_price":     trade.get("entry_price") or trade.get("entry") or data.get("entry_price"),
                        "stop_loss":       trade.get("stop_loss") or data.get("stop_loss"),
                        "take_profit":     trade.get("take_profit") or data.get("take_profit"),
                        "probability_score": trade.get("probability_score") or data.get("probability_score") or data.get("probability"),
                        "rr_ratio":        trade.get("rr_ratio") or data.get("rr_ratio") or data.get("risk_reward"),
                        "timeframe":       trade.get("timeframe") or data.get("timeframe"),
                        "session":         trade.get("session") or data.get("session"),
                    }
            except Exception:
                continue

    # Fallback: regex-parse key values from plain text
    def find_num(keys):
        for k in keys:
            m = re.search(rf"{k}\s*[:=]\s*([-+]?\d*\.?\d+)", text, re.IGNORECASE)
            if m:
                try:
                    return float(m.group(1))
                except ValueError:
                    pass
        return None

    def find_word(keys):
        for k in keys:
            m = re.search(rf"{k}\s*[:=]\s*([A-Za-z/]+)", text, re.IGNORECASE)
            if m:
                return m.group(1)
        return None

    return {
        "pair":            find_word(["pair", "symbol"]),
        "signal":          find_word(["signal", "direction", "side"]),
        "entry_price":     find_num(["entry_price", "entry"]),
        "stop_loss":       find_num(["stop_loss", "sl"]),
        "take_profit":     find_num(["take_profit", "tp"]),
        "probability_score": find_num(["probability_score", "probability", "confidence"]),
        "rr_ratio":        find_num(["rr_ratio", "risk_reward", "rr"]),
        "timeframe":       find_word(["timeframe"]),
        "session":         find_word(["session"]),
    }


def _best_setup_from_market_agent() -> tuple[dict, str]:
    """Fallback: use MarketAgent directly to find best A+ setup."""
    results = market_agent.analyze_market()
    best = None

    for item in (results if isinstance(results, list) else []):
        for setup in item.get("setups", []):
            prob = float(setup.get("probability_score", setup.get("confidence", 0)) or 0)
            if best is None or prob > float(best["setup"].get("probability_score", 0) or 0):
                best = {"item": item, "setup": setup, "prob": prob}

    if not best:
        return {}, "No A+ setup found from market agent fallback."

    setup = best["setup"]
    item  = best["item"]
    signal = {
        "pair":             setup.get("pair") or item.get("pair"),
        "signal":           setup.get("signal") or setup.get("direction"),
        "entry_price":      setup.get("entry_price") or setup.get("entry"),
        "stop_loss":        setup.get("stop_loss"),
        "take_profit":      setup.get("take_profit"),
        "probability_score": best["prob"],
        "rr_ratio":         setup.get("rr_ratio"),
        "timeframe":        setup.get("timeframe") or item.get("timeframe"),
        "session":          item.get("killzone", {}).get("info", {}).get("killzone"),
        "fvg_present":      item.get("fvg", {}).get("present", False),
        "order_blocks_present": item.get("order_blocks", {}).get("present", False),
        "liquidity_confirmed":  item.get("liquidity", {}).get("liquidity_confirmation", {}).get("confirmed", False),
        "sweeps_detected":  len(item.get("sweeps", {}).get("buy_side", []) + item.get("sweeps", {}).get("sell_side", [])) > 0,
        "analysis_notes":   setup.get("analysis_notes", ""),
    }
    return signal, f"Market agent fallback — best setup: {signal.get('pair')} {signal.get('signal')} @ {signal.get('probability_score')}%"


@router.get("/crew-analysis")
def crew_analysis():
    source = "crew"
    raw_text = ""
    warning = None
    signal = {}
    analysis_text = ""

    try:
        result = trading_crew.kickoff()
        raw_text = _to_text(result)
        signal = _extract_signal(raw_text)
        analysis_text = raw_text

        # If crew returned NO_TRADE fall back to market agent
        if not signal.get("pair") or "NO_TRADE" in raw_text.upper():
            source = "fallback_market_agent"
            warning = "Crew returned no valid setup — using market agent fallback"
            signal, analysis_text = _best_setup_from_market_agent()

    except Exception as exc:
        source = "fallback_market_agent"
        warning = f"Crew execution failed: {exc}"
        signal, analysis_text = _best_setup_from_market_agent()

    return {
        "signal": signal,
        "raw_result": raw_text,
        "analysis": analysis_text,
        "source": source,
        "warning": warning,
    }
