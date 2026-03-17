---
name: stock-ticker
description: Retrieve real-time stock prices with market-aware context and caching
allowed-tools:
  - get_stock_quote
  - get_market_context
  - stream_stock_ticks
---

# STOCK TICKER SKILL

## PURPOSE
Provide accurate, real-time stock pricing and a concise explanation
of recent market movement using authoritative market data tools.

## CONSTRAINTS
- Use tools for all price data
- Do not estimate or hallucinate prices
- Do not provide investment advice
- Respect market hours context

## INPUT
- Stock ticker symbol (e.g. AAPL, TSLA)
- Optional intent:
  - current price
  - intraday movement
  - live updates

## PROCEDURE

1. Extract the stock ticker symbol.
2. Call `get_market_context` to determine:
   - Market open/closed
   - Trading session (pre, regular, after-hours)
3. Call `get_stock_quote` with the ticker.
4. If the user requests live updates:
   - Call `stream_stock_ticks`
   - Stop after meaningful change or user-specified duration
5. Synthesize a concise factual summary.

## COMPLETION
Return:
- Current price
- Market session
- Direction (up/down/flat)
- Brief factual explanation (if available)

