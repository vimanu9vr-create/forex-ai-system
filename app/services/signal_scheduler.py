"""
SignalScheduler — background daemon that runs the VALIDATED live strategy and,
for each NEW signal, sends a Telegram alert and records a PAPER trade.

It uses the disciplined trend + structure engine (live_pair_scanner →
trade_levels) on config.STRATEGY_PAIRS / STRATEGY_TIMEFRAME — default
GBPUSD + EURUSD on Daily, the only edge that survived cost + out-of-sample
testing. Auto-started on FastAPI startup.

De-duplication: a given setup (pair + side + entry) is alerted/recorded once,
so a daily signal that persists for hours isn't re-sent every cycle.
"""

import time
import threading
from datetime import datetime

from app.config import SCAN_INTERVAL_SECONDS, STRATEGY_PAIRS, STRATEGY_TIMEFRAME
from app.services.signal_service import get_live_signals
from app.services.telegram_service import send_elite_setup_alert
from app.services.trade_logger import save_trade


def _rr_num(rr):
    try:
        return float(str(rr).replace("1:", "").strip()) if rr else 0.0
    except (TypeError, ValueError):
        return 0.0


class SignalScheduler:
    def __init__(self, interval_seconds: int = None):
        self.interval_seconds = interval_seconds or SCAN_INTERVAL_SECONDS
        self.running = False
        self.thread = None
        self._seen: set = set()      # dedup across cycles: "pair_side_entry"

    # ── Lifecycle ─────────────────────────────────────────────────────────
    def start(self):
        if self.running:
            print("[Scheduler] Already running — skipping duplicate start")
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True, name="SignalScheduler")
        self.thread.start()
        print(f"[Scheduler] Started — {STRATEGY_PAIRS} @ {STRATEGY_TIMEFRAME}, "
              f"every {self.interval_seconds}s")

    def stop(self):
        self.running = False
        print("[Scheduler] Stopped")

    # ── Main loop ─────────────────────────────────────────────────────────
    def _loop(self):
        while self.running:
            try:
                self._scan_and_alert()
            except Exception as e:
                print(f"[Scheduler] Unhandled error in scan cycle: {e}")
            for _ in range(self.interval_seconds * 2):   # responsive stop()
                if not self.running:
                    return
                time.sleep(0.5)

    def _scan_and_alert(self):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'─'*60}\n[Scheduler] Scan {ts} — {STRATEGY_PAIRS} @ {STRATEGY_TIMEFRAME}\n{'─'*60}")

        try:
            signals = get_live_signals(force=True)
        except Exception as e:
            print(f"[Scheduler] Scan error: {e}")
            return

        if not signals:
            print("[Scheduler] No valid setup right now (disciplined NO-TRADE)")
            return

        sent = 0
        for s in signals:
            pair, sig = s.get("pair"), s.get("signal")
            entry, sl, tp = s.get("entry"), s.get("stop_loss"), s.get("take_profit")

            key = f"{pair}_{sig}_{entry}"
            if key in self._seen:
                continue                      # this exact setup already alerted
            self._seen.add(key)

            conf = s.get("confluence_score", 0)
            rr = s.get("risk_reward", "")
            print(f"[Scheduler] 🎯 {pair} {sig} entry={entry} sl={sl} tp={tp} rr={rr} conf={conf}")
            try:
                send_elite_setup_alert(
                    pair=pair, signal=sig,
                    entry_price=entry, stop_loss=sl, take_profit=tp,
                    probability_score=conf, rr_ratio=_rr_num(rr),
                    timeframe=s.get("timeframe", STRATEGY_TIMEFRAME),
                    analysis_notes=s.get("setup", ""),
                )
                save_trade(pair=pair, signal=sig, entry_price=entry,
                           stop_loss=sl, take_profit=tp, probability=conf, status="open")
                sent += 1
                print(f"[Scheduler] ✅ alert + paper trade recorded: {pair} {sig}")
            except Exception as e:
                print(f"[Scheduler] ❌ failed for {pair}: {e}")

        print(f"[Scheduler] Cycle complete — {len(signals)} signal(s), {sent} new")


# ── Singleton ──────────────────────────────────────────────────────────────
_scheduler: SignalScheduler | None = None


def get_scheduler() -> SignalScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = SignalScheduler()
    return _scheduler


def start_signal_scheduler() -> SignalScheduler:
    s = get_scheduler()
    s.start()
    return s


def stop_signal_scheduler():
    get_scheduler().stop()
