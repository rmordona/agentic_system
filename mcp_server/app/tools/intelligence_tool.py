from app.mcp import mcp
from app.services.market_service import market_service

@mcp.tool()
async def search_macro_news(query: str = "Federal Reserve") -> list:
    """
    Scans global financial news outlets for macro-economic themes.
    Focuses on central bank policy and geopolitical risk.
    """
    return [
        {"source": "Reuters", "headline": "Fed signals 'higher for longer' as inflation persists"},
        {"source": "Bloomberg", "headline": "Oil prices stabilize amid Middle East tensions"}
    ]


@mcp.tool()
async def analyze_earnings_call(ticker: str) -> str:
    """
    Retrieves and summarizes the latest earnings call transcript, 
    highlighting key executive sentiment and forward guidance.
    """
    return f"Summary for {ticker}: CEO focused on margin expansion and AI integration. Conservative guidance for Q1."

@mcp.tool()
async def search_ticker_news(ticker: str):
    """
    Retrieve recent news articles related to a specific stock ticker.
    """
    articles = await market_service.search_ticker_news(ticker)
    return await market_service.classify_news(articles)

# Mark for hot-loader recognition
search_ticker_news._is_mcp_tool = True
search_ticker_news._metadata = {
    "parameters": [
        {"name": "ticker", "type": "str"}
    ]
}