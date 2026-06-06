"""
ExecutionAgent — Validates, executes, logs, and alerts elite A+ trade setups.

Flow:
  1. Extract and validate setup fields
  2. Run RiskManager checks (prob, RR, smart money)
  3. On approval: save to memory + DB, send Telegram alert
  4. On rejection: send rejection alert, return REJECTED
"""
from datetime import datetime

from app.memory.trade_memory import add_trade_to_history
from app.risk.risk_manager import RiskManager
from app.services.telegram_service import send_elite_setup_alert
from app.services.trade_logger import save_trade


class ExecutionAgent:

    def __init__(self):
        self.risk_manager = RiskManager()

    # ─────────────────────────────────────────────────────────────────────
    # Main entry point
    # ─────────────────────────────────────────────────────────────────────
    def execute_trade(self, setup: dict) -> dict:
        print("=" * 55)
        print("🚀 EXECUTION AGENT — PROCESSING SETUP")
        print("=" * 55)

        if not setup or not isinstance(setup, dict):
            return {"status": "REJECTED", "reason": "No setup provided"}

        # ── Extract fields ────────────────────────────────────────────────
        pair             = setup.get("pair", "N/A")
        signal           = setup.get("signal") or setup.get("direction", "N/A")
        entry_price      = setup.get("entry_price")
        stop_loss        = setup.get("stop_loss")
        take_profit      = setup.get("take_profit")
        probability      = float(setup.get("probability_score") or setup.get("confidence") or 0)
        rr_ratio         = float(setup.get("rr_ratio") or 0)
        timeframe        = setup.get("timeframe", "H1")
        session          = setup.get("session", "LIVE")
        analysis_notes   = setup.get("analysis_notes", "")
        lot_size         = float(setup.get("lot_size") or 0.01)

        # Smart money context
        fvg_present          = bool(setup.get("fvg_present"))
        order_blocks_present = bool(setup.get("order_blocks_present"))
        liquidity_confirmed  = bool(setup.get("liquidity_confirmed"))
        killzone_active      = bool(setup.get("killzone_active"))
        sweeps_detected      = bool(setup.get("sweeps_detected"))

        smart_money = {
            "fvg_present":         fvg_present,
            "order_blocks":        order_blocks_present,
            "liquidity_confirmed": liquidity_confirmed,
            "sweeps_detected":     sweeps_detected,
        }

        print(f"   Pair:        {pair}  {signal}")
        print(f"   Entry/SL/TP: {entry_price} / {stop_loss} / {take_profit}")
        print(f"   Probability: {probability:.0f}%  RR: {rr_ratio:.2f}")
        print(f"   SM Signals:  FVG={fvg_present} OB={order_blocks_present} "
              f"LIQ={liquidity_confirmed} SWP={sweeps_detected}")

        # ── Risk validation ───────────────────────────────────────────────
        risk = self.risk_manager.validate_trade(setup)

        if not risk["approved"]:
            print(f"❌ REJECTED — {risk['message']}")
            for r in risk.get("rejections", []):
                print(f"   • {r}")

            # Rejection Telegram alert (non-fatal)
            try:
                send_elite_setup_alert(
                    pair=pair,
                    signal=signal,
                    signal_active=False,
                    probability_score=probability,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    rr_ratio=rr_ratio,
                    timeframe=timeframe,
                    session=session,
                    analysis_notes=f"REJECTED — {risk['message']}",
                    status="REJECTED",
                    smart_money=smart_money,
                )
            except Exception as e:
                print(f"   ⚠ Telegram rejection alert failed: {e}")

            return {
                "status":            "REJECTED",
                "pair":              pair,
                "signal":            signal,
                "reason":            risk["message"],
                "rejections":        risk.get("rejections", []),
                "warnings":          risk.get("warnings", []),
                "probability_score": probability,
                "smart_money":       smart_money,
            }

        print("✅ RISK VALIDATION PASSED")

        # ── Build trade result ────────────────────────────────────────────
        executed_at = datetime.utcnow().isoformat() + "Z"
        trade_result = {
            "trade_id":        f"{pair}_{datetime.utcnow().timestamp():.0f}",
            "pair":            pair,
            "signal":          signal,
            "entry_price":     entry_price,
            "stop_loss":       stop_loss,
            "take_profit":     take_profit,
            "lot_size":        lot_size,
            "probability_score": probability,
            "rr_ratio":        rr_ratio,
            "timeframe":       timeframe,
            "session":         session,
            "status":          "EXECUTED",
            "execution_type":  "PAPER_TRADE",
            "executed_at":     executed_at,
            "smart_money":     smart_money,
        }

        # ── Save to in-memory history ─────────────────────────────────────
        try:
            add_trade_to_history({"setup": setup, "trade_result": trade_result})
            print("✅ Saved to memory")
        except Exception as e:
            print(f"⚠ Memory save failed (non-fatal): {e}")

        # ── Save to database ──────────────────────────────────────────────
        try:
            trade_id = save_trade(
                pair=pair,
                signal=signal,
                entry_price=float(entry_price or 0),
                stop_loss=float(stop_loss or 0),
                take_profit=float(take_profit or 0),
                probability=probability,
            )
            print(f"✅ Saved to DB (id={trade_id})")
        except Exception as e:
            print(f"⚠ DB save failed (non-fatal): {e}")

        # ── Send Telegram A+ alert ────────────────────────────────────────
        try:
            send_elite_setup_alert(
                pair=pair,
                signal=signal,
                signal_active=True,
                probability_score=probability,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                rr_ratio=rr_ratio,
                timeframe=timeframe,
                session=session,
                analysis_notes=analysis_notes,
                status="EXECUTED",
                smart_money=smart_money,
            )
            print("✅ Telegram A+ alert sent")
        except Exception as e:
            print(f"⚠ Telegram alert failed (non-fatal): {e}")

        print("=" * 55)
        print(f"✅ TRADE EXECUTED: {pair} {signal} @ {entry_price}")
        print("=" * 55)

        return {
            "status":       "SUCCESS",
            "message":      f"A+ trade executed: {pair} {signal}",
            "trade_result": trade_result,
        }

    # ─────────────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────────────
    def close_trade(self, trade_id: str) -> dict:
        print(f"🔒 CLOSING TRADE: {trade_id}")
        return {"trade_id": trade_id, "status": "CLOSED"}

    def get_open_positions(self) -> list:
        try:
            from app.memory.trade_memory import trade_history
            return [
                t["trade_result"]
                for t in trade_history
                if t.get("trade_result", {}).get("status") == "EXECUTED"
            ]
        except Exception as e:
            print(f"⚠ get_open_positions error: {e}")
            return []

    def get_execution_summary(self) -> dict:
        positions = self.get_open_positions()
        return {
            "execution_engine": "ACTIVE",
            "total_positions":  len(positions),
            "buy_positions":    sum(1 for p in positions if str(p.get("signal", "")).upper() == "BUY"),
            "sell_positions":   sum(1 for p in positions if str(p.get("signal", "")).upper() == "SELL"),
        }
