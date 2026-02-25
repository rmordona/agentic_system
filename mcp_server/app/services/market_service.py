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

        logger.info("SystemContext initialization complete")     

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

market_service = MarketService()


