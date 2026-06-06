from fastapi import APIRouter
from app.agents.market_agent import MarketAgent
from app.services.signal_service import get_live_signals, signal_cache_status

router = APIRouter()
_market_agent = MarketAgent()


@router.get("/agent-analysis")
def agent_analysis():
    """
    Full smart money market scan across all pairs.
    Returns ranked setups with probability scores and smart money context.
    """
    return _market_agent.analyze_market()


@router.get("/agent-analysis/best")
def best_setup():
    """
    Returns only the single best A+ setup from the market agent scan.
    Filters: probability >= 80, smart money >= 2/4, RR >= 1.5
    """
    results = _market_agent.analyze_market()
    best = None
    best_prob = 0

    for item in results:
        for setup in item.get("setups", []):
            prob = float(setup.get("probability_score") or setup.get("confidence") or 0)
            rr   = float(setup.get("rr_ratio") or 0)
            sm_count = sum([
                item.get("fvg", {}).get("present", False),
                item.get("order_blocks", {}).get("present", False),
                item.get("liquidity", {}).get("liquidity_confirmation", {}).get("confirmed", False),
                len((item.get("sweeps") or {}).get("buy_side", []) +
                    (item.get("sweeps") or {}).get("sell_side", [])) > 0,
            ])

            is_a_plus = prob >= 80 and rr >= 1.5 and sm_count >= 2

            if is_a_plus and prob > best_prob:
                best_prob = prob
                best = {
                    "pair":                   item.get("pair"),
                    "signal":                 setup.get("signal") or setup.get("direction"),
                    "entry_price":            setup.get("entry_price"),
                    "stop_loss":              setup.get("stop_loss"),
                    "take_profit":            setup.get("take_profit"),
                    "probability_score":      prob,
                    "rr_ratio":               rr,
                    "timeframe":              setup.get("timeframe") or item.get("timeframe"),
                    "session":                item.get("killzone", {}).get("info", {}).get("killzone"),
                    "fvg_present":            item.get("fvg", {}).get("present", False),
                    "order_blocks_present":   item.get("order_blocks", {}).get("present", False),
                    "liquidity_confirmed":    item.get("liquidity", {}).get("liquidity_confirmation", {}).get("confirmed", False),
                    "sweeps_detected":        len((item.get("sweeps") or {}).get("buy_side", []) +
                                                   (item.get("sweeps") or {}).get("sell_side", [])) > 0,
                    "killzone_active":        item.get("killzone", {}).get("active", False),
                    "smart_money_count":      sm_count,
                    "analysis_notes":         setup.get("analysis_notes", ""),
                    "grade":                  "A+" if prob >= 85 else "A",
                }

    if not best:
        return {
            "status": "NO_TRADE",
            "reason": "No setup currently meets A+ criteria (prob>=80, RR>=1.5, SM>=2/4)",
            "signal_cache": signal_cache_status(),
        }

    return {"status": "A_PLUS_SETUP", "setup": best}
