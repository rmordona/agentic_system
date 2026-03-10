from __future__ import annotations
import sys
import os

# 1. Get the absolute path to the 'agentic_system' root
# We go up 4 levels from: ./agentic_system/workspaces/stockticker_assistant/tools/mcp/intelligence.py
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))

# 2. Add it to the search path if it's not already there
if root_path not in sys.path:
    sys.path.append(root_path)

from llm.model_manager import ModelManager

from app.services.market.macro_market import  HTTPMarketDataProvider, MacroMarketDataService
from app.services.market.alpaca_news_provider import  AlpacaNewsProvider
from app.services.market.sentiment_classifiers import  SentimentClassifier, MarketSentiment, EmotionSentiment
from app.services.market.ticker_extractor import  TickerExtractor


from app.config_api_manager import ConfigApiManager

from app.logger import AgentLogger

logger = AgentLogger.get_logger(  component="system")

cfg = ConfigApiManager()
_API_KEY = cfg.api_key
_API_SECRET = cfg.api_secret

class MarketService:

    async def fetch_alpaca_market(self):
        provider = HTTPMarketDataProvider(
            api_key=_API_KEY,
            api_secret=_API_SECRET
        )
        
        macro_service = MacroMarketDataService(provider)

        macro_payload = await macro_service.fetch_macro_market_data()

        logger.info(f"Macro Payload: {macro_payload}")

        logger.info("Fetch Alpaca Market completed")     

        return macro_payload

    async def search_ticker_news(self, ticker: str):
        # To Call: asyncio.run(run_news_analysis("AAPL"))

        # 1. Instantiate the class (creates the connection)
        provider = AlpacaNewsProvider( api_key=_API_KEY, api_secret=_API_SECRET)
        
        # 2. Invoke the specific method
        # This returns the DataEnvelope we designed earlier
        envelope = await provider.get_ticker_news(ticker, limit=3)
        logger.info(f"Completed News Search: {envelope}")
        # 3. Use the data
        if envelope["metadata"]["status"] == "success":
            articles = envelope["payload"]["articles"]
            for news in articles:
                logger.info(f"Found: {news['headline']} ({news['timestamp']})")
            return articles
        else:
            logger.info(f"Error: {envelope['metadata']['details']}")

        return []

    
    async def classify_news(self, articles: list) -> list:

        llm = ModelManager.spin_model()

        classifier = SentimentClassifier(llm_client=llm)

        sentiments = []

        for article in articles:

            content = classifier.fetch_content(article["url"])

            result = await classifier.classify(
                headline=article["headline"],
                content=content,
                sentiment_enum=MarketSentiment
            )
            content = { 'headline': article["headline"], 'sentiment' : result.content }
            logger.info(f"Classified header: {content}")
            sentiments.append(content)

        return { 'headlines' : sentiments }

    
    async def extract_ticker(self, user_intent: str):
        llm = ModelManager.spin_model()
        extractor = TickerExtractor(llm)
        logger.info(f"Now Executing Extract Ticker: {user_intent}")
        result = await extractor.extract(user_intent)
        return { 'ticker' : result.content }

    async def get_correlation_tracking(self, symbol_a: str, symbol_b: str, window: int = 20) -> Dict[str, Any]:
        provider = HTTPMarketDataProvider(
            api_key=_API_KEY,
            api_secret=_API_SECRET
        )
        
        macro_service = MacroMarketDataService(provider)

        macro_payload = await macro_service.get_correlation_tracking(symbol_a, symbol_b, window)

        logger.info(f"Macro Payload: {macro_payload}")

        logger.info("Getting correlation completed")       

        return macro_payload


    async def get_trend_report(self, ticker: str, days: int = 30) -> Dict[str, Any]:
        """
        Calculates Technical Signals: SMA, Trend Direction, and Volume Profile.
        """
        logger.info(f"Generating trend report for {ticker} over {days} days")
        
        try:
            # 1. Fetch historical data (using the method we added earlier)
            prices = await self.provider.get_historical_bars(ticker, limit=days + 50)
            
            if len(prices) < days:
                return {"error": f"Insufficient data for {ticker}. Need {days} bars."}

            # 2. Basic Calculations
            current_price = prices[-1]
            sma_50 = sum(prices[-50:]) / 50 if len(prices) >= 50 else sum(prices) / len(prices)
            
            # 3. Determine Trend Sentiment
            price_change_pct = ((prices[-1] - prices[0]) / prices[0]) * 100
            trend_direction = "BULLISH" if prices[-1] > sma_50 else "BEARISH"
            
            return {
                "summary": {
                    "ticker": ticker.upper(),
                    "current_price": round(current_price, 2),
                    "period_days": days,
                    "trend_direction": trend_direction
                },
                "technical_signals": {
                    "price_change_pct": round(price_change_pct, 2),
                    "distance_from_sma50": round(((current_price - sma_50) / sma_50) * 100, 2),
                    "volatility_ratio": round(max(prices) / min(prices), 2)
                },
                "recommendation_engine": "HOLD" if abs(price_change_pct) < 5 else ("BUY" if trend_direction == "BULLISH" else "SELL")
            }
        except Exception as e:
            logger.error(f"Trend report failed for {ticker}: {e}")
            return {"error": "Technical Analysis Engine Timeout", "success": False}

market_service = MarketService()