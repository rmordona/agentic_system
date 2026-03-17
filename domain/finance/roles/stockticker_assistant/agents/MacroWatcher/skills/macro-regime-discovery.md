---
name: macro-regime-discovery
description: Establishes the global economic "Weather Report" before trading.
allowed_tools: [get_market_regime_data, search_macro_news]
---
# RUNBOOK: Macro Discovery

## Phase 1: Quantitative Anchoring
- Call `get_market_regime_data`.
- Identify the "Real Rate" (Interest Rate minus CPI).
- **Constraint:** If VIX > 30, set `regime` to `CRISIS_MODE` immediately.

## Phase 2: Narrative Overlay
- Call `search_macro_news` for "Federal Reserve" and "Geopolitical Risk".
- Cross-reference numerical data with current narrative trends.

## Phase 3: Verdict
- Determine `trade_permission`. If `regime` is `CRISIS_MODE`, permission MUST be `false`.
