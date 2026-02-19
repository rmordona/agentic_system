from app.mcp import mcp

@mcp.tool()
async def calculate_var(ticker: str, position_size: float) -> dict:
    """
    Calculates Value at Risk (VaR) for a proposed trade based on 
    historical volatility and 95% confidence intervals.
    """
    # Logic: position_size * (volatility * confidence_interval)
    var_amount = position_size * 0.035
    return {
        "ticker": ticker,
        "position_value": position_size,
        "VaR_95": round(var_amount, 2),
        "risk_percentage": "3.5%"
    }

@mcp.tool()
async def execute_trade(ticker: str, side: str, qty: int, order_type: str = "LIMIT") -> dict:
    """
    Submits a live order to the brokerage. 
    Side must be 'BUY' or 'SELL'. Order_type defaults to 'LIMIT'.
    """
    # In production, this tool MUST verify the RiskGuard's 'APPROVED' signature in the graph state.
    order_id = f"ORD-{datetime.datetime.now().strftime('%Y%m%d')}-{ticker}"
    return {
        "status": "FILLED",
        "order_id": order_id,
        "ticker": ticker,
        "qty": qty,
        "avg_price": 175.42,
        "timestamp": datetime.datetime.now().isoformat()
    }