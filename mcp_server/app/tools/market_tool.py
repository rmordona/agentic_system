from app.mcp_instance import mcp
from app.services.market_service import market_service

from app.logger import AgentLogger

logger = AgentLogger.get_logger(  component="system")

@mcp.tool()
async def fetch_alpaca_market():
    """
    Fetch the latest market data from ALPACA API.
    """
    result = await market_service.fetch_alpaca_market()
    logger.info(f"[fetch_alpaca_market] Result from mcp tool: {result}")
    return result

# Mark for hot-loader recognition
fetch_alpaca_market._is_mcp_tool = True
fetch_alpaca_market._metadata = {
    "parameters": []
}


@mcp.tool()
async def extract_ticker(user_intent: str):
    """
    Identify the stock ticker mentioned in a user query or intent.
    """
    logger.info(f"[extract_ticker] Entering mcp tool: {user_intent}")
    result = await market_service.extract_ticker({"user_intent": user_intent})
    logger.info(f"[extract_ticker] Result from mcp tool: {result}")
    return result

@mcp.tool()
async def get_market_regime_data(
    market_data: dict, 
    timestamp: str, 
    risk_mode: str = "NORMAL"
) -> dict:
    """
    Analyzes macro indicators and returns the structured regime state 
    required by the MacroWatcher Agent.
    """
    # 1. Internal Logic: Process raw indicators
    vix = 14.85
    yield_curve = "inverted"
    
    # 2. Logic to determine 'regime' based on indicators
    # In a real system, this would be a sophisticated model
    if vix < 20 and yield_curve != "inverted":
        current_regime = "BULL_EXPANSION"
    elif vix > 30:
        current_regime = "VOLATILE_SIDEWAYS"
    else:
        # Default for your current 'inverted' yield curve example
        current_regime = "VOLATILE_SIDEWAYS"

    # 3. Logic to determine 'risk_index' [1-10]
    # Inverted yield + high rates might mean higher risk
    calculated_risk = 6 

    # 4. Construct the response according to AGENT.md
    return { "macro_analysis" :
        {
            "regime": current_regime,
            "risk_index": calculated_risk,
            "key_drivers": [
                f"VIX at {vix}",
                f"Yield curve is {yield_curve}",
                f"Input price: {market_data.get('price')}"
            ],
            "trade_permission": True if calculated_risk < 7 else False
        }
    }

@mcp.tool()
async def get_ticker_stats(ticker: str) -> dict:
    """
    Returns high-precision technical data for a specific stock ticker, 
    including Moving Averages (MA50, MA200), RSI, and Z-Score volatility.
    """
    # Integration point: yFinance or AlphaVantage
    return {
        "ticker": ticker.upper(),
        "current_price": 175.40,
        "MA50": 170.10,
        "MA200": 162.50,
        "RSI": 58.2,
        "volatility_z_score": 1.1,
        "daily_volume": 45000000
    }


@mcp.tool()
async def get_correlation_tracking(symbol_a: str, symbol_b: str, window: int = 20) -> dict:
    """
    Tracks the price correlation between two assets (e.g., SPY and BTC). 
    Used to detect decoupling or risk-on/risk-off shifts.
    
    Args:
        symbol_a (str): First ticker symbol.
        symbol_b (str): Second ticker symbol.
        window (int): Number of trading days for the lookback (default 20).
    """
    logger.info(f"[get_correlation_tracking] Checking {symbol_a} vs {symbol_b}")
    # Assuming macro_market_service is initialized in your market_service or available here
    result = await market_service.get_correlation_tracking(symbol_a, symbol_b, window)
    return result

# Explicit metadata for the hot-loader if your system requires it
get_correlation_tracking._is_mcp_tool = True
get_correlation_tracking._metadata = {
    "parameters": ["symbol_a", "symbol_b", "window"]
}


@mcp.tool()
async def analyze_market_trends(ticker: str, days: int = 30):
    """
    Analyzes price action, volume trends, and sentiment for a specific ticker.
    
    Args:
        ticker (str): The stock symbol (e.g., 'TSLA', 'SPY').
        days (int): Lookback period for trend analysis.
    """
    # Logic to fetch and analyze data
    return await market_service.get_trend_report(ticker, days)

@mcp.tool()
async def get_trend_report(ticker: str, days: int = 30) -> dict:
    """
    Analyzes price action and technical indicators to determine market momentum.
    
    Args:
        ticker (str): The stock symbol (e.g., 'TSLA', 'AAPL').
        days (int): Lookback window for trend analysis (Max 252).
    """
    # 1. Input Predicate/Validation
    if days > 252:
        return {"error": "Lookback period too long. Maximum is 252 trading days."}
    
    ticker = ticker.strip().upper()
    logger.info(f"[get_trend_report] Executing for {ticker}")

    # 2. Call Service
    result = await market_service.get_trend_report(ticker, days)
    return result

# Register for hot-loader
get_trend_report._is_mcp_tool = True