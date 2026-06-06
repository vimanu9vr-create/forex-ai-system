def detect_equal_highs(
    swing_highs,
    tolerance=None
):

    equal_highs = []

    for i in range(
        len(swing_highs) - 1
    ):

        current_high = swing_highs[i]

        next_high = swing_highs[i + 1]

        # Pip-relative tolerance: JPY-style pairs quote ~100+ (pip 0.01),
        # everything else uses pip 0.0001. Within ~2 pips counts as "equal".
        tol = tolerance
        if tol is None:
            pip = 0.01 if current_high["price"] >= 20 else 0.0001
            tol = 2 * pip

        difference = abs(
            current_high["price"] -
            next_high["price"]
        )

        if difference <= tol:

            equal_highs.append({
                "price": current_high["price"],
                "first_touch": current_high["timestamp"],
                "second_touch": next_high["timestamp"],
                "type": "buy_side_liquidity"
            })

    return equal_highs


def detect_equal_lows(
    swing_lows,
    tolerance=None
):

    equal_lows = []

    for i in range(
        len(swing_lows) - 1
    ):

        current_low = swing_lows[i]

        next_low = swing_lows[i + 1]

        # Pip-relative tolerance: JPY-style pairs quote ~100+ (pip 0.01),
        # everything else uses pip 0.0001. Within ~2 pips counts as "equal".
        tol = tolerance
        if tol is None:
            pip = 0.01 if current_low["price"] >= 20 else 0.0001
            tol = 2 * pip

        difference = abs(
            current_low["price"] -
            next_low["price"]
        )

        if difference <= tol:

            equal_lows.append({
                "price": current_low["price"],
                "first_touch": current_low["timestamp"],
                "second_touch": next_low["timestamp"],
                "type": "sell_side_liquidity"
            })

    return equal_lows