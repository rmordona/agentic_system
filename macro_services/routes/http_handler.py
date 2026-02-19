# routes/http_handler.py
from fastapi import APIRouter, Depends

class MCPRouter:
    def __init__(self, market_handler: MarketHandler):
        self.router = APIRouter()
        self.market = market_handler
        self._setup_routes()

    def _setup_routes(self):
        @self.router.post("/news")
        async def get_news(payload: dict):
            # XHR style endpoint
            ticker = payload.get("ticker")
            return await self.market.fetch_news(ticker)
