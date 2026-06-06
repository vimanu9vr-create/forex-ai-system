"""
ReflectionAgent — Analyzes recent trade performance to guide the adaptive system.

Sources data from:
  1. In-memory trade_history (fast, recent executions this session)
  2. Database trades table (persistent, historical data)

Returns win rate (0.0–1.0), P&L, and pattern insights.
"""
from app.memory.trade_memory import get_trade_history


class ReflectionAgent:

    def analyze_performance(self) -> dict:
        """
        Analyze trade performance from memory + database.
        Returns metrics used by AdaptiveAgent and CrewAI reflection task.
        """
        trades = self._load_trades()

        if not trades:
            return {
                "message":             "No trades to analyze yet",
                "total_trades":        0,
                "wins":                0,
                "losses":              0,
                "total_profit_loss":   0.0,
                "average_profit_loss": 0.0,
                "win_rate":            0.0,
                "best_pairs":          [],
                "best_sessions":       [],
                "recommendation":      "Insufficient data — use default confidence",
            }

        wins   = 0
        losses = 0
        total_pnl = 0.0
        pair_wins:    dict = {}
        pair_losses:  dict = {}
        session_wins: dict = {}

        for trade in trades:
            pnl     = self._extract_pnl(trade)
            pair    = self._extract_field(trade, "pair", "UNKNOWN")
            session = self._extract_field(trade, "session", "unknown")

            total_pnl += pnl

            if pnl > 0:
                wins += 1
                pair_wins[pair]    = pair_wins.get(pair, 0) + 1
                session_wins[session] = session_wins.get(session, 0) + 1
            elif pnl < 0:
                losses += 1
                pair_losses[pair] = pair_losses.get(pair, 0) + 1

        total = len(trades)
        win_rate = wins / total if total > 0 else 0.0
        avg_pnl  = total_pnl / total if total > 0 else 0.0

        # Top performing pairs (by win count)
        best_pairs = sorted(pair_wins, key=pair_wins.get, reverse=True)[:3]

        # Worst pairs (avoid these)
        worst_pairs = sorted(pair_losses, key=pair_losses.get, reverse=True)[:2]

        # Best sessions
        best_sessions = sorted(session_wins, key=session_wins.get, reverse=True)[:2]

        # Qualitative recommendation
        if win_rate >= 0.70:
            recommendation = "Strong performance — maintain current strategy"
        elif win_rate >= 0.55:
            recommendation = "Average performance — continue with standard filters"
        elif win_rate >= 0.40:
            recommendation = "Below average — tighten entry criteria, reduce lot size"
        else:
            recommendation = "Poor performance — only take 90%+ probability setups"

        return {
            "total_trades":         total,
            "wins":                 wins,
            "losses":               losses,
            "total_profit_loss":    round(total_pnl, 2),
            "average_profit_loss":  round(avg_pnl, 2),
            "win_rate":             round(win_rate, 4),   # 0.0–1.0
            "win_rate_pct":         round(win_rate * 100, 1),
            "best_pairs":           best_pairs,
            "worst_pairs":          worst_pairs,
            "best_sessions":        best_sessions,
            "recommendation":       recommendation,
            "message": (
                f"Analyzed {total} trades | "
                f"Win rate: {win_rate*100:.1f}% | "
                f"Avg P&L: ${avg_pnl:.2f}"
            ),
        }

    # ── Private helpers ───────────────────────────────────────────────────
    def _load_trades(self) -> list:
        """Load trades from memory + database, deduplicated."""
        trades = []

        # 1. In-memory trades (this session)
        try:
            mem = get_trade_history()
            for entry in mem.get("trades", []):
                result = entry.get("trade_result", entry)
                trades.append(result)
        except Exception as e:
            print(f"[ReflectionAgent] Memory load error: {e}")

        # 2. Database trades (persistent history)
        try:
            from app.database import SessionLocal
            from app.models.trade_model import Trade
            db = SessionLocal()
            try:
                db_trades = db.query(Trade).order_by(Trade.opened_at.desc()).limit(100).all()
                for t in db_trades:
                    trades.append({
                        "pair":    t.pair,
                        "signal":  t.signal,
                        "pnl":     t.pnl,
                        "status":  t.status,
                        "session": t.killzone_active or "unknown",
                    })
            finally:
                db.close()
        except Exception as e:
            print(f"[ReflectionAgent] DB load error (non-fatal): {e}")

        return trades

    def _extract_pnl(self, trade: dict) -> float:
        """Extract PnL from trade dict regardless of field name."""
        for key in ("pnl", "profit_loss", "pl", "profit"):
            val = trade.get(key)
            if val is not None:
                try:
                    return float(val)
                except (TypeError, ValueError):
                    pass
        return 0.0

    def _extract_field(self, trade: dict, field: str, default: str) -> str:
        """Safely extract a string field."""
        val = trade.get(field)
        return str(val).upper() if val else default
