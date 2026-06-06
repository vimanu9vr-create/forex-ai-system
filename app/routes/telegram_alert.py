from fastapi import APIRouter

from app.agents.market_agent import MarketAgent
from app.services.telegram_service import (
    send_elite_setup_alert,
    send_telegram_message,
)

router = APIRouter()
agent = MarketAgent()


@router.get("/send-alert")
def telegram_alert():
    """
    Manual trigger: scan all pairs and push a Telegram alert for EVERY pair
    that currently has a valid setup (not just the single best EURUSD).

    This is the on-demand "snapshot" path. Strict, automatic alerts are handled
    separately by SignalScheduler (every 15 min, prob >= 80%).
    """
    results = agent.analyze_market()

    sent = []
    for item in results:
        pair = item.get("pair")
        setups = item.get("setups", [])
        if not setups:
            continue

        # Best setup for this pair (highest probability / confidence)
        best = max(
            setups,
            key=lambda s: float(s.get("probability_score") or s.get("confidence") or 0),
        )

        smart_money = {
            "fvg_present":         item.get("fvg", {}).get("present", False),
            "order_blocks":        item.get("order_blocks", {}).get("present", False),
            "liquidity_confirmed": item.get("liquidity", {}).get("liquidity_confirmation", {}).get("confirmed", False),
            "sweeps_detected":     len(item.get("sweeps", {}).get("buy_side", []) +
                                       item.get("sweeps", {}).get("sell_side", [])) > 0,
        }

        try:
            send_elite_setup_alert(
                pair=pair,
                signal=best.get("signal"),
                signal_active=True,
                probability_score=best.get("probability_score") or best.get("confidence") or 0,
                entry_price=best.get("entry_price"),
                stop_loss=best.get("stop_loss"),
                take_profit=best.get("take_profit"),
                rr_ratio=best.get("rr_ratio", 0),
                timeframe=best.get("timeframe", "H4/H1/M15"),
                session=item.get("killzone", {}).get("info", {}).get("killzone", "LIVE"),
                analysis_notes=best.get("analysis_notes", ""),
                smart_money=smart_money,
            )
            sent.append({
                "pair":         pair,
                "signal":       best.get("signal"),
                "probability":  best.get("probability_score") or best.get("confidence"),
                "entry":        best.get("entry_price"),
                "stop_loss":    best.get("stop_loss"),
                "take_profit":  best.get("take_profit"),
                "rr_ratio":     best.get("rr_ratio"),
            })
        except Exception as e:
            print(f"[send-alert] Telegram failed for {pair}: {e}")

    if not sent:
        send_telegram_message("📭 No valid setups across scanned pairs right now.")
        return {"message": "No valid setups found", "sent": []}

    return {"message": f"Sent {len(sent)} Telegram alert(s)", "sent": sent}
