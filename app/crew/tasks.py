from crewai import Task
from app.crew.agents import market_analyst_agent, reflection_agent, execution_agent

# ─────────────────────────────────────────────────────────────────────────────
# TASK 1 — Elite Market Analysis
# Scans all pairs, applies strict A+ filters, returns ONE best setup
# ─────────────────────────────────────────────────────────────────────────────
market_analysis_task = Task(
    description="""
You are a proprietary trading-desk analyst. Combine ICT concepts, Smart Money
Concepts (SMC), the Wyckoff method, Volume Profile, market-structure analysis,
institutional liquidity theory, and macro context into ONE decision.

Call the analyze_market tool ONCE. Per pair it returns: higher_timeframe_bias,
direction, entry_price, stop_loss, take_profit, rr_ratio, invalidation,
bos_confirmed, choch_confirmed, fvg_present, order_blocks_present,
liquidity_confirmed, sweeps_detected, killzone_active, session, probability_score,
poc, value_area_high, value_area_low (Market Profile), wyckoff_phase, wyckoff_bias,
macro_event_risk, macro_high_impact, macro_headlines.

Select the SINGLE best A+ setup that passes ALL of these — reject everything else:
- Direction MUST match higher_timeframe_bias (trade only with the HTF trend).
- A liquidity sweep must precede entry (sweeps_detected = true).
- BOS or CHOCH confirmed (bos_confirmed or choch_confirmed = true).
- Entry at an FVG / order-block retracement (fvg_present or order_blocks_present = true).
- Risk:Reward >= 3.0 (1:3 minimum).
- Skip low-probability conditions: no clear HTF trend, price mid-range, conflicting signals.

HONESTY RULES — real capital is at risk:
- Use ONLY numbers returned by the tool. NEVER fabricate prices or levels.
- Volume Profile, Wyckoff AND macro (economic calendar + news) are all provided by
  the tool now — use those values; never fabricate prices, levels or news.
- If macro_event_risk is "elevated" (a high-impact release is imminent for the
  pair's currencies), say so and prefer NO_TRADE or wait until after the event.
- If no pair passes every filter, return NO_TRADE.
""",
    expected_output="""
Output a machine-readable JSON block FIRST (one line, FLAT — no nested objects):
{"pair": "EURUSD", "signal": "BUY", "entry_price": 1.08250, "stop_loss": 1.07900, "take_profit": 1.09250, "probability_score": 85, "rr_ratio": 3.1, "invalidation": 1.07900, "session": "London", "timeframe": "H1/M15"}

Then a markdown analysis with EXACTLY these sections:

## Higher-Timeframe Trend
## Liquidity Sweep — Where Retail Is Trapped
## Structure Shift (BOS / CHOCH)
## Entry — FVG / Order-Block Retracement
## Trade Plan
- Entry / Stop Loss / Take Profit (1:3+)
- Invalidation: the exact level and what price action voids the idea
- Management: TP1 @ 1R (close 1/3, SL->breakeven), TP2 @ 2R (close 1/3, trail), TP3 @ target (runner)
## Where Institutions Are Accumulating / Distributing
## Volume Profile (Market Profile / TPO)
Use the tool's poc / value_area_high / value_area_low. State whether entry and
targets sit inside the value area, at the POC, or in a low-activity (rejection) zone.
## Wyckoff
Use the tool's wyckoff_phase / wyckoff_bias (accumulation vs distribution, spring/upthrust) — it must agree with your trade direction.
## Macro
Use macro_event_risk, macro_high_impact (upcoming high-impact releases) and macro_headlines.
If event risk is elevated, name the event and state your caution (wait / reduce size / stand aside).

End with EXACTLY this line, then a 2-3 sentence answer:
**Would I take this trade with my own capital? Why or why not?**

If nothing qualifies, output ONLY:
{"status": "NO_TRADE", "reason": "<one concrete reason>"}
""",
    agent=market_analyst_agent,
)

# ─────────────────────────────────────────────────────────────────────────────
# TASK 2 — Performance Reflection
# Reviews recent trade history to validate the proposed setup
# ─────────────────────────────────────────────────────────────────────────────
reflection_task = Task(
    description="""
Use the analyze_performance tool to review recent trade history.
Cross-reference the proposed setup from the market analyst with historical
winning patterns to validate or flag it.

Focus on:
- Which sessions generate the highest win rate
- Which pairs are performing best this cycle
- Setup quality patterns from recent winners
- Any recurring failure patterns to avoid

Provide a concise APPROVED or FLAG_FOR_REVIEW assessment with reason.
""",
    expected_output="""
{
  "win_rate": 0.72,
  "total_trades_analyzed": 15,
  "best_performing_session": "London",
  "best_performing_pairs": ["EURUSD", "GBPUSD"],
  "setup_assessment": "APPROVED",
  "assessment_reason": "Proposed EURUSD BUY matches top winning pattern: London + FVG + BOS",
  "risk_notes": "No concerns — RR and probability within historical winners range"
}
""",
    agent=reflection_agent,
    context=[market_analysis_task],
)

# ─────────────────────────────────────────────────────────────────────────────
# TASK 3 — Trade Execution
# Takes validated setup and executes it with full Telegram alert
# ─────────────────────────────────────────────────────────────────────────────
execution_task = Task(
    description="""
You are the execution engine. Read the setup from market_analysis_task context.

If setup is valid (status != NO_TRADE):
1. Pass the complete setup dict to the execute_trade tool
2. Confirm execution with full trade details

If setup is NO_TRADE or below thresholds:
1. Return REJECTED with clear reason
2. Do NOT fabricate any trade

Hard rules:
- Minimum probability: 80%
- Minimum RR: 3.0 (1:3)
- Do NOT ask for confirmation
- Do NOT guess or fabricate prices
- Execute or reject — no middle ground
""",
    expected_output="""
{
  "status": "EXECUTED",
  "pair": "EURUSD",
  "signal": "BUY",
  "entry_price": 1.08250,
  "stop_loss": 1.07900,
  "take_profit": 1.08900,
  "probability_score": 88,
  "rr_ratio": 1.8,
  "session": "London",
  "execution_timestamp": "2025-01-01T10:00:00Z",
  "telegram_sent": true,
  "rejection_reason": null
}
""",
    agent=execution_agent,
    context=[market_analysis_task, reflection_task],
)

# ─────────────────────────────────────────────────────────────────────────────
# Fallback / standalone tasks (kept for backward compatibility)
# ─────────────────────────────────────────────────────────────────────────────
risk_validation_task = Task(
    description="""
Validate trade setup against risk parameters.
Check: max 2% position size, min 1.5 RR, max 5% portfolio exposure.
Return approved/rejected with metrics.
""",
    expected_output="Risk validation result: approved/rejected with reasons",
    agent=execution_agent,
)

technical_validation_task = Task(
    description="""
Validate technical setup against key price levels.
Check entry/SL/TP alignment with support/resistance and smart money zones.
Return technical score 0-100.
""",
    expected_output="Technical validation score and confirmation details",
    agent=market_analyst_agent,
)

sentiment_alignment_task = Task(
    description="""
Check if the proposed setup aligns with current session bias and sentiment.
Return alignment score and confirmation.
""",
    expected_output="Sentiment alignment analysis with score",
    agent=reflection_agent,
)
