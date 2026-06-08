"""
IntradayAlertScheduler — self-contained daemon that pushes high-grade (A+/A)
top-down liquidity-sweep setups to Telegram during the London / New York killzones.

SEPARATE from SignalScheduler (the daily-edge alerter): different engine, its own
thread, faster cadence. To stay cheap it does NOTHING outside an entry killzone
(no API calls), and de-duplicates so the same setup isn't re-sent each cycle.
"""

import time
import threading
from datetime import datetime

from app.config import INTRADAY_ALERT_SESSIONS
from app.services.intraday_signal_service import get_intraday_signals
from app.services.telegram_service import send_telegram_message
from app.smart_money.killzones import in_killzone

INTERVAL_SECONDS = 300            # 5 min while a killzone is open
ENTRY_TFS = ("15min", "5min")
ALERT_GRADES = ("A+", "A")        # only the disciplined setups get pushed
_KZ_TO_SESSION = {"London Open": "london", "New York Open": "newyork"}


def _format_alert(s: dict, tf: str) -> str:
    arrow = "🟢" if s["signal"] == "BUY" else "🔴"
    # New York underperformed in backtest — flag its alerts so they aren't treated as the
    # validated London edge.
    exp = "  ⚠ EXPERIMENTAL" if s.get("killzone") == "New York Open" else ""
    return "\n".join([
        f"⚡ INTRADAY SWEEP — {s.get('grade')}  ({tf}){exp}",
        f"{arrow} {s['pair']} | {s['signal']} | {s.get('killzone')}",
        f"HTF bias: {s.get('htf_bias')} (D:{s.get('htf_daily')} 4H:{s.get('htf_4h')})",
        f"Swept: {s.get('swept_liquidity')}   MSS: {s.get('mss_level')}",
        f"Entry: {s['entry']} ({s.get('entry_basis')})",
        f"SL:    {s['stop_loss']}  ({s.get('risk_pips')} pips)",
        f"TP1:   {s['take_profit']}  ({s.get('risk_reward')}R) -> close 50%, SL to BE",
        f"Runner: {s.get('runner_target')} (HTF draw)",
        "🤖 ForexAI Intraday",
    ])


class IntradayAlertScheduler:
    def __init__(self, interval_seconds: int = INTERVAL_SECONDS, tfs=ENTRY_TFS):
        self.interval_seconds = interval_seconds
        self.tfs = tfs
        self.running = False
        self.thread = None
        self._seen: set = set()

    def start(self):
        if self.running:
            print("[IntradayAlerts] Already running")
            return
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True, name="IntradayAlertScheduler")
        self.thread.start()
        print(f"[IntradayAlerts] Started — A+/A sweeps to Telegram in killzones, every {self.interval_seconds}s")

    def stop(self):
        self.running = False
        print("[IntradayAlerts] Stopped")

    def _loop(self):
        while self.running:
            try:
                self._scan_and_alert()
            except Exception as e:
                print(f"[IntradayAlerts] cycle error: {e}")
            for _ in range(self.interval_seconds * 2):   # responsive stop()
                if not self.running:
                    return
                time.sleep(0.5)

    def _scan_and_alert(self):
        # Alert the session that matches the CURRENT killzone (London during London, NY during
        # NY), if that session is enabled in INTRADAY_ALERT_SESSIONS. Idle/no API calls otherwise.
        session = _KZ_TO_SESSION.get(in_killzone().get("killzone"))
        if not session or session not in INTRADAY_ALERT_SESSIONS:
            return
        sent = 0
        for tf in self.tfs:
            try:
                signals = get_intraday_signals(force=True, tf=tf, session=session)
            except Exception as e:
                print(f"[IntradayAlerts] scan {tf} {session} error: {e}")
                continue
            for s in signals:
                if s.get("grade") not in ALERT_GRADES or not s.get("fresh"):
                    continue
                key = f"{s['pair']}_{s['signal']}_{tf}_{s['entry']}"
                if key in self._seen:
                    continue
                self._seen.add(key)
                if send_telegram_message(_format_alert(s, tf)):
                    sent += 1
        if sent:
            print(f"[IntradayAlerts] {datetime.utcnow().isoformat()} — sent {sent} alert(s) [{session}]")


# ── Singleton ──────────────────────────────────────────────────────────────
_scheduler = None


def get_intraday_alert_scheduler() -> IntradayAlertScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = IntradayAlertScheduler()
    return _scheduler


def start_intraday_alert_scheduler() -> IntradayAlertScheduler:
    s = get_intraday_alert_scheduler()
    s.start()
    return s


def stop_intraday_alert_scheduler():
    get_intraday_alert_scheduler().stop()
