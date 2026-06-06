import time

from app.database import (SessionLocal)

from app.models.trade_model import (Trade)
from app.services.market_data import (
    get_forex_intraday
)
from app.services.candle_formatter import(
    format_twelvedata_data
)

from app.services.telegram_service import(
    send_telegram_alert
)
def monitor_trades():
    print("TRADE MONITOR STARTED")

    while True:
        try:
            db = SessionLocal()
            open_trades = db.query(Trade).filter(Trade.status == "OPEN").all()

            for trade in open_trades:
                pair = trade.pair
                raw_data = get_forex_intraday(pair)
                candles = format_twelvedata_data(raw_data)

                if not candles:
                    continue

                current_price = candles[-1]["close"]

                if trade.signal == "BUY":
                    if current_price >= trade.take_profit:
                        trade.status = "closed"
                        trade.pnl = 2.0
                        db.commit()
                        send_telegram_alert(
                            pair=pair,
                            direction="TP HIT",
                            entry_price=trade.entry_price,
                            stop_loss=trade.stop_loss,
                            take_profit=trade.take_profit,
                            probability=trade.probability_score,
                            session="LIVE",
                            risk_reward="+2R"
                        )
                        print(f"TP HIT {pair}")

                    elif current_price <= trade.stop_loss:
                        trade.status = "closed"
                        trade.pnl = -1.0
                        db.commit()
                        send_telegram_alert(
                            pair=pair,
                            direction="SL HIT",
                            entry_price=trade.entry_price,
                            stop_loss=trade.stop_loss,
                            take_profit=trade.take_profit,
                            probability=trade.probability_score,
                            session="LIVE",
                            risk_reward="-1R"
                        )
                        print(f"SL HIT {pair}")

                elif trade.signal == "SELL":
                    if current_price <= trade.take_profit:
                        trade.status = "closed"
                        trade.pnl = 2.0
                        db.commit()
                        send_telegram_alert(
                            pair=pair,
                            direction="TP HIT",
                            entry_price=trade.entry_price,
                            stop_loss=trade.stop_loss,
                            take_profit=trade.take_profit,
                            probability=trade.probability_score,
                            session="LIVE",
                            risk_reward="+2R"
                        )
                        print(f"TP HIT {pair}")

                    elif current_price >= trade.stop_loss:
                        trade.status = "closed"
                        trade.pnl = -1.0
                        db.commit()
                        send_telegram_alert(
                            pair=pair,
                            direction="SL HIT",
                            entry_price=trade.entry_price,
                            stop_loss=trade.stop_loss,
                            take_profit=trade.take_profit,
                            probability=trade.probability_score,
                            session="LIVE",
                            risk_reward="-1R"
                        )
                        print(f"SL HIT {pair}")

            db.close()
            time.sleep(60)

        except Exception as e:
            print(f"MONITOR ERROR: {e}")
            time.sleep(60)
