# mcp_tools.py

import time
import asyncio
from datetime import datetime, time as dtime
from functools import lru_cache

# -----------------------------
# Market hours utilities
# -----------------------------

NYSE_OPEN = dtime(9, 30)
NYSE_CLOSE = dtime(16, 0)

def market_context():
    now = datetime.utcnow().time()
    if now < NYSE_OPEN:
        return "pre-market"
    elif NYSE_OPEN <= now <= NYSE_CLOSE:
        return "open"
    else:
        return "after-hours"


# -----------------------------
# Cached stock quote
# -----------------------------

@lru_cache(maxsize=512)
def _cached_quote(ticker: str):
    # Simulated external API call
    return {
        "ticker": ticker,
        "price": 182.43,
        "currency": "USD",
        "timestamp": datetime.utcnow().isoformat()
    }

async def get_stock_quote(ticker: str) -> dict:
    return _cached_quote(ticker)


# -----------------------------
# Market context tool
# -----------------------------

async def get_market_context() -> dict:
    return {
        "market": "NYSE",
        "session": market_context(),
        "timestamp": datetime.utcnow().isoformat()
    }


# -----------------------------
# Streaming stock ticks
# -----------------------------

async def stream_stock_ticks(ticker: str):
    """
    Async generator for live price updates.
    Intended for streaming-capable agents.
    """
    base_price = 182.00
    for i in range(5):
        await asyncio.sleep(1)
        yield {
            "ticker": ticker,
            "price": round(base_price + i * 0.12, 2),
            "timestamp": datetime.utcnow().isoformat()
        }

