from fastapi import APIRouter
from sqlalchemy import func
from app.database import SessionLocal
from app.models.trade_model import Trade

router = APIRouter()


@router.get("/dashboard")
def dashboard():
    db = SessionLocal()
    try:
        total_trades = db.query(Trade).count()
        open_trades = db.query(Trade).filter(Trade.status == "open").count()
        closed_trades = db.query(Trade).filter(Trade.status == "closed").count()

        # Winning = closed trades with pnl > 0
        all_closed = db.query(Trade).filter(Trade.status == "closed").all()
        winning_trades = sum(1 for t in all_closed if _to_float(t.pnl) > 0)
        losing_trades = sum(1 for t in all_closed if _to_float(t.pnl) < 0)

        # Win rate based on closed trades
        if closed_trades > 0:
            win_rate = round((winning_trades / closed_trades) * 100, 1)
        else:
            win_rate = 0

        # Total PnL across all closed trades
        total_pnl = sum(_to_float(t.pnl) for t in all_closed)

        # Best pair = pair with most winning trades
        pair_wins: dict = {}
        for t in all_closed:
            if _to_float(t.pnl) > 0 and t.pair:
                pair_wins[t.pair] = pair_wins.get(t.pair, 0) + 1

        best_pair = max(pair_wins, key=pair_wins.get) if pair_wins else _most_traded_pair(db)

        # Market bias from real smart-money structure (BOS + CHoCH).
        # Analyse the pair we're most engaged with: latest open trade's pair,
        # else the best pair, else a sensible default.
        latest = (
            db.query(Trade)
            .filter(Trade.status == "open")
            .order_by(Trade.opened_at.desc())
            .first()
        )
        bias_pair = (latest.pair if latest and latest.pair else best_pair) or "EURUSD"
        if not bias_pair or len(bias_pair) != 6:
            bias_pair = "EURUSD"
        try:
            from app.smart_money.bias import compute_market_bias
            market_bias = compute_market_bias(bias_pair).get("bias", "Neutral").upper()
        except Exception as e:
            print(f"[dashboard] market bias computation failed for {bias_pair}: {e}")
            market_bias = "NEUTRAL"

        # Bot status: running if there are open trades
        bot_status = "RUNNING" if open_trades > 0 else "IDLE"

    finally:
        db.close()

    return {
        "bot_status": bot_status,
        "total_trades": total_trades,
        "open_trades": open_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": win_rate,
        "total_pnl": round(total_pnl, 2),
        "best_pair": (best_pair or "N/A").upper(),
        "market_bias": market_bias,
    }


def _to_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _most_traded_pair(db) -> str:
    """Fallback: pair with most total trades."""
    result = (
        db.query(Trade.pair, func.count(Trade.id).label("cnt"))
        .filter(Trade.pair.isnot(None))
        .group_by(Trade.pair)
        .order_by(func.count(Trade.id).desc())
        .first()
    )
    return result[0] if result else "N/A"
