from fastmcp import FastMCP

intelligence_mcp = FastMCP("SentimentEngine")

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

@intelligence_mcp.tool()
async def search_ticker_news(ticker: str) -> list:
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


if __name__ == "__main__":
    # This is the magic line that keeps the process alive
    # and starts the JSON-RPC communication over Stdio
    intelligence_mcp.run()
