from __future__ import annotations
import logging
import requests
from datetime import datetime, timezone
from typing import Dict, Any, Optional


from app.logger import AgentLogger

logger = AgentLogger.get_logger(  component="system")


# ==============================
# Concrete Market Data Provider
# ==============================

class HTTPMarketDataProvider:
    """
    Alpaca Market Data HTTP Provider
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        timeout: float = 5.0,
    ):
        self.base_url = "https://data.alpaca.markets/v2"
        #self.base_url = "https://paper-api.alpaca.markets/v2"
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = timeout

    def _request(self, endpoint: str) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint}"

        headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret,
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=self.timeout,
        )

        response.raise_for_status()
        return response.json()


    async def get_latest_quote(self, symbol: str) -> Dict[str, float]:
        endpoint = f"stocks/{symbol}/bars/latest"
        data = self._request(endpoint)

        bar = data.get("bar")
        if not bar:
            raise ValueError(f"No bar data returned: {data}")

        return {
            "price": float(bar["c"]),
            "volume": float(bar["v"]),
        }

    async def get_historical_bars(
            self, 
            symbol: str, 
            timeframe: str = "1Day", 
            limit: int = 20
        ) -> list[float]:
            """
            Fetches historical price bars from Alpaca.
            Returns a list of closing prices (floats).
            """
            # Alpaca V2 historical stocks endpoint
            endpoint = f"stocks/{symbol}/bars"
            
            # Query parameters for the GET request
            params = {
                "timeframe": timeframe,
                "limit": limit,
                "adjustment": "all",  # Handles splits and dividends automatically
                "feed": "sip",        # Standard consolidated feed
                "sort": "asc"         # Oldest to newest
            }

            url = f"{self.base_url}/{endpoint}"
            headers = {
                "APCA-API-KEY-ID": self.api_key,
                "APCA-API-SECRET-KEY": self.api_secret,
            }

            try:
                # We use requests here to match your _request pattern, 
                # but wrapping it in an async-friendly way if needed.
                response = requests.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                data = response.json()

                bars = data.get("bars", [])
                if not bars:
                    logger.warning(f"No historical bars found for {symbol}")
                    return []

                # Extract the 'c' (close) price from each bar
                # Alpaca Bar Schema: {'t': time, 'o': open, 'h': high, 'l': low, 'c': close, 'v': volume}
                closing_prices = [float(bar["c"]) for bar in bars]
                
                logger.info(f"Retrieved {len(closing_prices)} bars for {symbol}")
                return closing_prices

            except requests.exceptions.HTTPError as e:
                logger.error(f"Alpaca API Error for {symbol}: {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error fetching bars for {symbol}: {e}")
                raise


# ===================================
# Macro Market Data Service
# ===================================

class MacroMarketDataService:
    """
    Service responsible for:
    - Fetching macro benchmark data
    - Formatting it for get_market_regime_data tool
    - Enforcing safe fallback policy
    """

    def __init__(
        self,
        provider: HTTPMarketDataProvider,
        benchmark_symbol: str = "SPY",  # S&P 500
        default_risk_mode: str = "NORMAL",
    ):
        self.provider = provider
        self.benchmark_symbol = benchmark_symbol
        self.default_risk_mode = default_risk_mode

    async def fetch_macro_market_data(self) -> Dict[str, Any]:
        logger.info("Starting macro market data fetch")

        try:
            quote = await self.provider.get_latest_quote(self.benchmark_symbol)

            payload = {
                "market_data": {
                    "price": quote["price"],
                    "volume": quote["volume"],
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "risk_mode": self.default_risk_mode,
            }

            logger.info("Macro market data fetched successfully")
            return payload

        except Exception as e:
            logger.exception("Macro data fetch failed — switching to CONSERVATIVE mode")

            return {
                "market_data": {
                    "price": 0.0,
                    "volume": 0.0,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "risk_mode": "CONSERVATIVE",
            }

    async def get_correlation_tracking(self, symbol_a: str, symbol_b: str, window: int = 20) -> Dict[str, Any]:
        """
        Calculates the Pearson correlation coefficient between two assets 
        over a specified lookback window.
        """
        logger.info(f"Calculating correlation between {symbol_a} and {symbol_b}")
        try:
            # Fetch bars in parallel (or sequentially if your provider isn't fully async yet)
            prices_a = await self.provider.get_historical_bars(symbol_a, limit=window)
            prices_b = await self.provider.get_historical_bars(symbol_b, limit=window)

            if len(prices_a) != len(prices_b) or len(prices_a) < 2:
                raise ValueError("Insufficient data points for correlation")

            # Calculate Pearson Correlation
            correlation = np.corrcoef(prices_a, prices_b)[0, 1]

            return {
                "pair": f"{symbol_a.upper()}/{symbol_b.upper()}",
                "correlation_coefficient": round(float(correlation), 4),
                "window_days": window,
                "status": "stable" if abs(correlation) > 0.7 else "decoupled",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Correlation check failed: {e}")
            return {"error": str(e), "success": False}


