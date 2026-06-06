import os
import requests
from app.config import (
    TELEGRAM_BOT_TOKEN as CONFIG_BOT_TOKEN,
    TELEGRAM_CHAT_ID as CONFIG_CHAT_ID,
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or CONFIG_BOT_TOKEN
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or CONFIG_CHAT_ID
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


def send_telegram_message(message: str) -> dict:
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(TELEGRAM_API_URL, params=payload, timeout=8)
        if response.ok:
            print("✓ Telegram message sent")
        else:
            print(f"✗ Telegram failed: {response.status_code} {response.text}")
        return response.json()
    except Exception as e:
        print(f"✗ Telegram error: {e}")
        return {}


def send_telegram_alert(
    pair=None,
    signal=None,
    probability_score=None,
    entry_price=None,
    stop_loss=None,
    take_profit=None,
    direction=None,
    session: str = "LIVE",
    risk_reward=None,
    probability=None,   # alias used by trade_monitor.py
) -> dict:
    """
    Generic signal / trade-event alert. Flexible args so both existing call
    sites work without change:
      - live_trading.py (positional): pair, signal, probability_score,
        entry_price, stop_loss, take_profit, direction, session, risk_reward
      - trade_monitor.py (keyword):   pair, direction="TP HIT"/"SL HIT",
        entry_price/stop_loss/take_profit, probability=, session, risk_reward
    """
    label = signal or direction or "SIGNAL"
    prob  = probability_score if probability_score is not None else probability
    up    = str(label).upper()
    emoji = "🟢" if up in ("BUY", "TP HIT") else "🔴" if up in ("SELL", "SL HIT") else "⚪"

    lines = [f"{emoji} {pair or 'N/A'}  |  {up}"]
    if signal and direction and direction != signal:
        lines.append(f"  Direction:   {direction}")
    if entry_price not in (None, "N/A"):
        lines.append(f"  Entry:       {entry_price}")
    if stop_loss not in (None, "N/A"):
        lines.append(f"  Stop Loss:   {stop_loss}")
    if take_profit not in (None, "N/A"):
        lines.append(f"  Take Profit: {take_profit}")
    if risk_reward not in (None, "N/A"):
        lines.append(f"  Risk/Reward: {risk_reward}")
    if prob not in (None, "N/A", 0):
        lines.append(f"  Probability: {prob}%")
    if session and session != "N/A":
        lines.append(f"  Session:     {session}")
    lines.append("🤖 ForexAI Engine")

    return send_telegram_message("\n".join(lines))


def send_elite_setup_alert(
    # Accept either a setup_data dict (positional) OR keyword args
    setup_data: dict = None,
    *,
    pair: str = None,
    signal: str = None,
    signal_direction: str = None,   # alias
    direction: str = None,           # alias
    entry_price=None,
    stop_loss=None,
    take_profit=None,
    probability_score=None,
    probability=None,                # alias
    confidence=None,
    rr_ratio=None,
    risk_reward=None,                # alias
    session: str = "LIVE",
    timeframe: str = "H1",
    analysis_notes: str = "",
    signal_active: bool = True,
    status: str = "ACTIVE",
    risk_percentage=None,
    multi_timeframe=None,
    smart_money: dict = None,
) -> bool:
    """
    Send elite A+ setup alert to Telegram.
    Accepts either a setup dict OR keyword arguments for flexibility.
    """
    # Merge dict + kwargs
    if setup_data and isinstance(setup_data, dict):
        pair            = pair or setup_data.get("pair", "N/A")
        signal          = signal or setup_data.get("signal", setup_data.get("signal_direction", "N/A"))
        entry_price     = entry_price if entry_price is not None else setup_data.get("entry_price", "N/A")
        stop_loss       = stop_loss if stop_loss is not None else setup_data.get("stop_loss", "N/A")
        take_profit     = take_profit if take_profit is not None else setup_data.get("take_profit", "N/A")
        probability_score = probability_score or setup_data.get("probability_score", setup_data.get("probability", 0))
        confidence      = confidence or setup_data.get("confidence", 0)
        rr_ratio        = rr_ratio or setup_data.get("rr_ratio", setup_data.get("risk_reward", 0))
        session         = session or setup_data.get("session", "LIVE")
        timeframe       = timeframe or setup_data.get("timeframe", "H1")
        analysis_notes  = analysis_notes or setup_data.get("analysis_notes", "")
        smart_money     = smart_money or setup_data.get("smart_money", {})

    # Resolve aliases
    signal          = signal or signal_direction or direction or "N/A"
    probability_score = probability_score or probability or 0
    rr_ratio        = rr_ratio or risk_reward or 0
    smart_money     = smart_money or {}

    # Ensure numeric rr_ratio
    try:
        rr_val = float(rr_ratio)
    except (TypeError, ValueError):
        rr_val = 0.0

    try:
        prob = float(probability_score)
    except (TypeError, ValueError):
        prob = 0.0

    # Format
    formatted_pair = f"{str(pair)[:3]}/{str(pair)[3:]}" if pair and len(str(pair)) == 6 else str(pair)
    signal_emoji   = "🟢" if str(signal).upper() == "BUY" else "🔴" if str(signal).upper() == "SELL" else "⚪"
    tier_emoji     = "🏆" if prob >= 90 else "⭐" if prob >= 80 else "✅"
    status_emoji   = "🚀 ACTIVE" if signal_active else "❌ REJECTED"

    fvg_mark    = "✓" if smart_money.get("fvg_present") else "✗"
    ob_mark     = "✓" if smart_money.get("order_blocks") else "✗"
    liq_mark    = "✓" if smart_money.get("liquidity_confirmed") else "✗"
    sweep_mark  = "✓" if smart_money.get("sweeps_detected") else "✗"

    message = (
        f"{tier_emoji} ELITE A+ SETUP {tier_emoji}\n\n"
        f"{'━'*38}\n"
        f"{signal_emoji}  {formatted_pair}  |  {str(signal).upper()}  |  {timeframe}\n"
        f"{'━'*38}\n\n"
        f"📊 TRADE LEVELS\n"
        f"  Entry:       {entry_price}\n"
        f"  Stop Loss:   {stop_loss}\n"
        f"  Take Profit: {take_profit}\n"
        f"  Risk/Reward: 1:{rr_val:.1f}\n\n"
        f"🎯 CONFLUENCE:   {prob:.0f}%\n"
        f"📍 SESSION:      {session}\n"
        f"📈 STATUS:       {status_emoji}\n\n"
        f"💡 SMART MONEY\n"
        f"  FVG:       {fvg_mark}\n"
        f"  OB:        {ob_mark}\n"
        f"  Liquidity: {liq_mark}\n"
        f"  Sweeps:    {sweep_mark}\n"
    )

    if analysis_notes:
        message += f"\n📝 {analysis_notes[:200]}\n"

    message += f"{'━'*38}\n🤖 ForexAI Engine"

    return send_telegram_message(message) != {}
