import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from alpaca.data.historical import NewsClient
from alpaca.data.requests import NewsRequest

from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(  component="system")

class AlpacaNewsProvider:
    def __init__(self, api_key: str, api_secret: str):
        self.client = NewsClient(api_key, api_secret)

    def get_ticker_news(self, ticker: str, limit: int = 5) -> Dict[str, Any]:
        try:
            # PRODUCTION TIP: Always specify a start date. 
            # Free tier data is often delayed by 15-20 minutes.
            # We'll look back 7 days to ensure we find articles.
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

            request_params = NewsRequest(
                symbols=ticker,
                limit=limit,
                start=thirty_days_ago, # Tell Alpaca exactly how far back to look
                sort="desc"            # Ensure you get the newest ones first
            )
            
            response = self.client.get_news(request_params)

            #logger.info(f"Response: {response}")

            raw_news = []
            if hasattr(response, "data") and isinstance(response.data, dict):
                raw_news = response.data.get("news", [])

            logger.info(f"Raw response type: {type(response)}")
            logger.info(f"Has news attr: {hasattr(response, 'news')}")
            logger.info(f"Response contents: {len(raw_news)} headlines")
            
            
            articles = []
            for article in raw_news:
                articles.append({
                    "headline": article.headline,
                    "url": article.url,
                    "timestamp": article.created_at.isoformat()
                })

            return self._create_envelope(
                status="success",
                payload={"ticker": ticker, "articles": articles},
                metadata={"count": len(articles)}
            )

        except Exception as e:
            return self._create_envelope(
                status="failed",
                payload=None,
                metadata={"error_details": str(e)}
            )

    # MUST be at the same indentation level as get_ticker_news
    def _create_envelope(self, status: str, payload: Optional[Dict], metadata: Dict) -> Dict[str, Any]:
        metadata["status"] = status
        return {
            "agent": "AlpacaNewsProvider",
            "type": "TickerNews",
            "version": "1.0",
            "created_at": datetime.utcnow().isoformat(),
            "payload": payload,
            "metadata": metadata
        }