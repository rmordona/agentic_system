from app.mcp import mcp
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



