trade_history = []

def add_trade_to_history(trade):
    trade_history.append(trade)

    return {
        "message": "Trade added to history",
        "total_trades": len(trade_history)
    }
def get_trade_history():
    return {
        "trades": trade_history,
        "total_trades": len(trade_history)
    }