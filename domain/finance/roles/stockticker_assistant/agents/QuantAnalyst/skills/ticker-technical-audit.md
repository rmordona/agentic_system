---
name: ticker-technical-audit
description: Mathematical validation of price action and volume.
allowed_tools: [get_ticker_stats]
---
# RUNBOOK: Technical Audit

## Phase 1: Trend Identification
- Call `get_ticker_stats`.
- Compare current price to MA200 and MA50.
- **Rule:** If Price < MA200, the bias is strictly `BEARISH` regardless of RSI.

## Phase 2: Momentum & Volatility
- Analyze RSI and Z-Score. 
- Identify if the ticker is "Overextended" (RSI > 75).

## Phase 3: Target Setting
- Calculate the `stop_loss` at the 20-day low.
- Calculate `take_profit` at the next major resistance level.
