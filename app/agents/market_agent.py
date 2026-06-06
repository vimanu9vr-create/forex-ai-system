"""
MarketAgent — Full institutional SMC analysis across 7 pairs.

Multi-timeframe approach:
  H4  → HTF bias (major swing structure, BOS/CHOCH)
  H1  → Intermediate OB / FVG / structure confirmation
  M15 → Entry precision (sweep confirmation, killzone timing)

Elite A+ criteria for Telegram alert:
  - probability_score >= 85%
  - at least 2/4 smart money signals (FVG, OB, liquidity, sweeps)
  - RR >= 1.5
"""

from app.services.market_data import get_multi_timeframe

from app.smart_money.structure import detect_swings
from app.smart_money.liquidity import detect_equal_highs, detect_equal_lows
from app.smart_money.sweeps import detect_buy_side_sweeps, detect_sell_side_sweeps
from app.smart_money.bos import detect_bullish_bos, detect_bearish_bos
from app.smart_money.choch import detect_bullish_choch, detect_bearish_choch
from app.smart_money.bias import determine_market_bias
from app.smart_money.setups import generate_trade_setup
from app.smart_money.multi_timeframe import analyze_multi_timeframe
from app.smart_money.fvg import detect_fvg
from app.smart_money.order_blocks import detect_order_blocks
from app.smart_money.killzones import detect_killzone
from app.smart_money.liquidity_confirmation import confirm_liquidity_grab
from app.smart_money.probability_engine import calculate_probability
from app.smart_money.market_profile import build_market_profile
from app.smart_money.wyckoff import detect_wyckoff
from app.services.macro_service import macro_context

FOREX_PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY",
    "AUDUSD", "USDCAD", "NZDUSD", "USDCHF",
]


class MarketAgent:
    def __init__(self):
        self.elite_threshold = 85
        self.min_sm_signals  = 2
        self.min_rr          = 1.5

    def is_elite_setup(self, setup: dict) -> bool:
        prob = float(setup.get("probability_score") or setup.get("confidence") or 0)
        rr   = float(setup.get("rr_ratio") or 0)
        sm   = sum([
            bool(setup.get("fvg_present")),
            bool(setup.get("order_blocks_present")),
            bool(setup.get("liquidity_confirmed")),
            bool(setup.get("sweeps_detected")),
        ])
        return prob >= self.elite_threshold and sm >= self.min_sm_signals and rr >= self.min_rr

    def analyze_market(self) -> list:
        results = []
        for pair in FOREX_PAIRS:
            try:
                result = self._analyze_pair(pair)
                if result:
                    results.append(result)
            except Exception as e:
                print(f"[MarketAgent] Error analyzing {pair}: {e}")
        return results

    def _analyze_pair(self, pair: str) -> dict | None:
        # ── Fetch H4 / H1 / M15 ──────────────────────────────────────────
        tf = get_multi_timeframe(pair)
        h4_candles  = tf["h4"]
        h1_candles  = tf["h1"]
        m15_candles = tf["m15"]

        if not h1_candles or len(h1_candles) < 20:
            print(f"[MarketAgent] Insufficient H1 data for {pair}")
            return None

        # ── H4: HTF bias ─────────────────────────────────────────────────
        htf_bias = "neutral"
        if h4_candles and len(h4_candles) >= 10:
            h4_sw   = detect_swings(h4_candles)
            h4_bbos = detect_bullish_bos(h4_candles, h4_sw["swing_highs"])
            h4_rbos = detect_bearish_bos(h4_candles, h4_sw["swing_lows"])
            h4_bchoch = detect_bullish_choch(h4_candles, h4_sw["swing_highs"])
            h4_rchoch = detect_bearish_choch(h4_candles, h4_sw["swing_lows"])
            h4_bias = determine_market_bias(h4_bbos, h4_rbos, h4_bchoch, h4_rchoch)
            htf_bias = h4_bias.get("bias", "neutral") if isinstance(h4_bias, dict) else "neutral"

        # ── H1: Intermediate structure ────────────────────────────────────
        swings      = detect_swings(h1_candles)
        swing_highs = swings["swing_highs"]
        swing_lows  = swings["swing_lows"]

        eq_highs        = detect_equal_highs(swing_highs)
        eq_lows         = detect_equal_lows(swing_lows)
        liquidity_zones = eq_highs + eq_lows

        buy_sweeps  = detect_buy_side_sweeps(h1_candles, liquidity_zones)
        sell_sweeps = detect_sell_side_sweeps(h1_candles, liquidity_zones)

        bull_bos   = detect_bullish_bos(h1_candles, swing_highs)
        bear_bos   = detect_bearish_bos(h1_candles, swing_lows)
        bull_choch = detect_bullish_choch(h1_candles, swing_highs)
        bear_choch = detect_bearish_choch(h1_candles, swing_lows)

        bias = determine_market_bias(bull_bos, bear_bos, bull_choch, bear_choch)

        # HTF overrides H1 bias direction
        if htf_bias != "neutral":
            if isinstance(bias, dict):
                bias["bias"] = htf_bias
                bias["higher_timeframe"] = htf_bias
            else:
                bias = {"bias": htf_bias, "higher_timeframe": htf_bias}

        # ── H1: FVG + Order Blocks ────────────────────────────────────────
        fvg_zones    = detect_fvg(h1_candles)
        order_blocks = detect_order_blocks(h1_candles)

        fvg_analysis = {
            "present": bool(fvg_zones.get("bullish_fvg_zones") or fvg_zones.get("bearish_fvg_zones")),
            "zones":   fvg_zones,
        }
        ob_analysis = {
            "present": bool(order_blocks.get("bullish_order_blocks") or order_blocks.get("bearish_order_blocks")),
            "blocks":  order_blocks,
        }

        # ── Killzone (M15 timing) ─────────────────────────────────────────
        killzone_info = detect_killzone()
        killzone_analysis = {
            "active": killzone_info.get("killzone") != "None",
            "info":   killzone_info,
        }

        # ── Liquidity confirmation ────────────────────────────────────────
        liq_conf = confirm_liquidity_grab(
            sweeps={"swept": len(buy_sweeps + sell_sweeps) > 0,
                    "sweeps": buy_sweeps + sell_sweeps},
            choch={"choch": len(bull_choch) + len(bear_choch) > 0,
                   "bullish": bull_choch, "bearish": bear_choch},
            killzone={"active": killzone_analysis["active"], "info": killzone_info},
            multi_timeframe={"valid": htf_bias != "neutral"},
        )
        liquidity_analysis = {
            "confirmed": liq_conf.get("liquidity_grab_confirmed", False),
            "reason":    liq_conf.get("reason", "No liquidity grab detected"),
            "zones":     [eq_highs + eq_lows],
        }

        # ── Probability score ─────────────────────────────────────────────
        prob_result = calculate_probability(
            sweeps={"swept": len(buy_sweeps + sell_sweeps) > 0,
                    "sweeps": buy_sweeps + sell_sweeps},
            choch={"choch": len(bull_choch) + len(bear_choch) > 0,
                   "bullish": bull_choch, "bearish": bear_choch},
            killzone=killzone_analysis,
            multi_timeframe={"valid": htf_bias != "neutral"},
            fvg=fvg_analysis,
            order_blocks=ob_analysis,
        )
        probability_score = prob_result.get("probability_score", 0)

        # ── Trade setups — M15 for entry precision ────────────────────────
        entry_candles = m15_candles if len(m15_candles) >= 20 else h1_candles

        setups = generate_trade_setup(
            bias,
            sell_sweeps,
            bull_bos,
            bull_choch,
            buy_sweeps,
            bear_bos,
            bear_choch,
            candles=entry_candles,
            pair=pair,
            fvg_zones=fvg_zones,
            order_blocks=order_blocks,
        )

        bias_text = bias.get("bias", "neutral") if isinstance(bias, dict) else str(bias)
        multi_tf  = analyze_multi_timeframe(bias_text, setups)
        timeframe = "H4 / H1 / M15" if htf_bias != "neutral" else "H1 / M15"

        # ── Enrich setups ─────────────────────────────────────────────────
        for setup in setups:
            setup["timeframe"]             = timeframe
            setup["analysis_notes"]        = multi_tf.get("reason", "")
            setup["higher_timeframe_bias"] = htf_bias
            setup["probability_score"]     = probability_score
            setup["fvg_present"]           = fvg_analysis["present"]
            setup["order_blocks_present"]  = ob_analysis["present"]
            setup["liquidity_confirmed"]   = liquidity_analysis["confirmed"]
            setup["killzone_active"]       = killzone_analysis["active"]
            setup["sweeps_detected"]       = len(buy_sweeps + sell_sweeps) > 0

            if self.is_elite_setup(setup):
                # Analysis only — Telegram alerting is centralised in
                # SignalScheduler (auto) and the /send-alert route (manual).
                # MarketAgent must NOT send here, or every analysis call
                # (dashboard polls, /agent-analysis, crew runs) would spam
                # alerts and elite setups would double-send.
                print(
                    f"🎯 ELITE A+: {pair} {setup.get('signal')} "
                    f"prob={setup.get('probability_score')}% "
                    f"entry={setup.get('entry_price')} "
                    f"sl={setup.get('stop_loss')} "
                    f"tp={setup.get('take_profit')} "
                    f"rr={setup.get('rr_ratio')}"
                )

        return {
            "pair":              pair,
            "bias":              bias,
            "timeframe":         timeframe,
            "htf_bias":          htf_bias,
            "multi_timeframe":   multi_tf,
            "probability_score": probability_score,
            "setups":            setups,
            "candle_counts": {
                "h4":  len(h4_candles),
                "h1":  len(h1_candles),
                "m15": len(m15_candles),
            },
            "swings": {"swing_highs": swing_highs, "swing_lows": swing_lows},
            "liquidity": {
                "equal_highs":            eq_highs,
                "equal_lows":             eq_lows,
                "liquidity_confirmation": liquidity_analysis,
            },
            "sweeps": {"buy_side": buy_sweeps, "sell_side": sell_sweeps},
            "bos":   {"bullish": bull_bos,   "bearish": bear_bos},
            "choch": {"bullish": bull_choch, "bearish": bear_choch},
            "fvg":          fvg_analysis,
            "order_blocks": ob_analysis,
            "killzone":     killzone_analysis,
            "market_profile": build_market_profile(h1_candles, pair),
            "wyckoff": detect_wyckoff(h1_candles, pair),
            "macro": macro_context(pair),
            "probability_details": prob_result,
        }
