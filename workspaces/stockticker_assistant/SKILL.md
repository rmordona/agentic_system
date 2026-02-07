---
name: stock-ticker
description: Retrieve real-time stock prices and market summaries
allowed-tools:
  - get_stock_price
  - get_market_summary
---

# STOCK TICKER SKILL

## OBJECTIVE
Provide accurate, up-to-date stock pricing and a concise explanation
of recent market movement.

## INPUT
- A stock ticker symbol (e.g. AAPL, TSLA)
- Optional time context (today, last hour, last week)

## PROCEDURE

1. Identify the stock ticker symbol from the user request.
2. Call `get_stock_price` with the ticker.
3. If the user asks for context or movement:
   a. Call `get_market_summary` for the ticker.
4. Synthesize a short, factual response.
5. Do not speculate. Do not provide financial advice.

## COMPLETION
Return a plain-language summary including:
- Current price
- Direction (up/down/flat)
- Brief explanation (if available)

