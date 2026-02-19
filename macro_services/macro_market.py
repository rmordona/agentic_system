import logging
import requests
from datetime import datetime, timezone
from typing import Dict, Any, Optional


from runtime.logger import AgentLogger

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


    def get_latest_quote(self, symbol: str) -> Dict[str, float]:
        endpoint = f"stocks/{symbol}/bars/latest"
        data = self._request(endpoint)

        bar = data.get("bar")
        if not bar:
            raise ValueError(f"No bar data returned: {data}")

        return {
            "price": float(bar["c"]),
            "volume": float(bar["v"]),
        }


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

    def fetch_macro_market_data(self) -> Dict[str, Any]:
        logger.info("Starting macro market data fetch")

        try:
            quote = self.provider.get_latest_quote(self.benchmark_symbol)

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




