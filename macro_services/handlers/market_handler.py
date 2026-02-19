# handlers/market_handler.py
class MarketHandler:
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        # Initialize Alpaca client here...

    async def fetch_news(self, ticker: str):
        # Your Alpaca news logic
        return {"ticker": ticker, "news": [...]}

# handlers/ticker_handler.py
class TickerHandler:
    @staticmethod
    def extract_from_intent(intent: str):
        # Your LLM-based extraction logic using the prompt we wrote
        return "TSLA"
