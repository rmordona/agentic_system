import sys
import os

# 1. Get the absolute path to the 'agentic_system' root
# We go up 4 levels from: ./agentic_system/workspaces/stockticker_assistant/tools/mcp/intelligence.py
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))

# 2. Add it to the search path if it's not already there
if root_path not in sys.path:
    sys.path.append(root_path)

from fastmcp import FastMCP
intelligence_mcp = FastMCP("SentimentEngine")

from runtime.config_api_manager import ConfigApiManager
cfg = ConfigApiManager()
_API_KEY = cfg.api_key
_API_SECRET = cfg.api_secret

from runtime.logger import AgentLogger
logger = AgentLogger.get_logger(component="system")

from llm.model_manager import ModelManager

@intelligence_mcp.tool()
async def search_macro_news(query: str = "Federal Reserve") -> list:
    """
    Scans global financial news outlets for macro-economic themes.
    Focuses on central bank policy and geopolitical risk.
    """
    return [
        {"source": "Reuters", "headline": "Fed signals 'higher for longer' as inflation persists"},
        {"source": "Bloomberg", "headline": "Oil prices stabilize amid Middle East tensions"}
    ]

async def search_ticker_news1(ticker: str) -> list:
    """
    Fetches the latest headlines and social velocity for a specific stock ticker.
    """
    return [
        {"headline": f"{ticker} reports 15% revenue growth in Q4", "sentiment": "Bullish"},
        {"headline": f"Analyst downgrades {ticker} to Neutral", "sentiment": "Bearish"}
    ]

@intelligence_mcp.tool()
async def analyze_earnings_call(ticker: str) -> str:
    """
    Retrieves and summarizes the latest earnings call transcript, 
    highlighting key executive sentiment and forward guidance.
    """
    return f"Summary for {ticker}: CEO focused on margin expansion and AI integration. Conservative guidance for Q1."




from macro_services.alpaca_news_provider import  AlpacaNewsProvider

@intelligence_mcp.tool()
async def search_ticker_news(ticker: str):
    # To Call: asyncio.run(run_news_analysis("AAPL"))

    # 1. Instantiate the class (creates the connection)
    provider = AlpacaNewsProvider( api_key=_API_KEY, api_secret=_API_SECRET)
    
    # 2. Invoke the specific method
    # This returns the DataEnvelope we designed earlier
    envelope = provider.get_ticker_news(ticker, limit=3)
    logger.info(f"Completed News Search: {envelope}")
    # 3. Use the data
    if envelope["metadata"]["status"] == "success":
        articles = envelope["payload"]["articles"]
        for news in articles:
            logger.info(f"Found: {news['headline']} ({news['timestamp']})")
        return await classify_news(articles)
    else:
        logger.info(f"Error: {envelope['metadata']['details']}")

    return []

from macro_services.sentiment_classifiers import  SentimentClassifier, MarketSentiment, EmotionSentiment
async def classify_news(articles: list) -> list:

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


if __name__ == "__main__":
    # This is the magic line that keeps the process alive
    # and starts the JSON-RPC communication over Stdio
    intelligence_mcp.run()
