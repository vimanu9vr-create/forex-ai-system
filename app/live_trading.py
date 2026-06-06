import time
from app.smart_money.live_pair_scanner import live_pair_scanner
from app.services.telegram_service import send_telegram_alert
from app.services.trade_logger import save_trade
from app.smart_money.risk_management import trade_levels

def live_trading_loop():
    print("LIVE AI FOREX TRADING SYSTEM STARTED")
    while True:
        try:
            print("Scanning for trading opportunities...")
            market_pairs = live_pair_scanner()

            if "best_pair" not in market_pairs:
                print("No valid trades found. Market pairs:", market_pairs)
                time.sleep(60)
            else:
                best_trade = market_pairs["best_pair"]
                pair = best_trade.get("pair")
                direction = best_trade.get("direction", "N/A")
                trade_level  = trade_levels(
                    pair=pair,
                    direction=direction,
                    candles=best_trade["candles"]

                )
                probability_score = best_trade.get("probability_score",0)
                signal = best_trade.get("sniper_signal", {}).get("entry")
                entry_price = best_trade.get(
                    "entry_price",
                    "N/A"
                )
                stop_loss = best_trade.get(
                    "stop_loss",
                    "N/A"
                )
                take_profit = best_trade.get(
                    "take_profit",
                    "N/A"
                )
                session = best_trade.get(
                    "session",
                    "N/A"
                )
                risk_reward = best_trade.get(
                    "risk_reward",
                    "N/A"
                )
                print(f"Best trade found: {pair} with probability score {probability_score} and signal {signal}")

                telegram_response = send_telegram_alert(pair, signal, probability_score,entry_price,stop_loss,take_profit,direction,session,risk_reward,)

                save_trade(
                    pair=pair,
                    signal=signal,
                    probability_score=probability_score,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    direction=direction,
                    session=session,
                    risk_reward=risk_reward,
                    trade_level=trade_level
                )
                print("Telegram alert sent. Response:", telegram_response)
            time.sleep(300)  # Wait for 5 minutes before scanning again
        except Exception as e:
            print("Error in live trading loop:", str(e))
            time.sleep(60)  # Wait for 1 minute before retrying
if __name__ == "__main__":
    live_trading_loop()