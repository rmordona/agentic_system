# mcp_tools.py

async def get_stock_price(ticker: str) -> dict:
    return {
        "ticker": ticker,
        "price": 182.43,
        "currency": "USD",
        "timestamp": "2026-02-02T15:30:00Z"
    }

async def get_market_summary(ticker: str) -> dict:
    return {
        "ticker": ticker,
        "movement": "up",
        "reason": "Strong earnings and positive analyst outlook"
    }

