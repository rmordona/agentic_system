import os
from datetime import datetime
from typing import Dict, Any, Optional
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestBarRequest

class AlpacaMarketProvider:
    def __init__(self):
        # Configuration pulled from environment
        self.api_key = os.getenv("APCA_API_KEY_ID")
        self.secret_key = os.getenv("APCA_API_SECRET_KEY")
        
        if not self.api_key or not self.secret_key:
            raise ValueError("Alpaca API keys not found in environment variables.")
            
        self.client = StockHistoricalDataClient(self.api_key, self.secret_key)

    def get_latest_price_and_volume(self, ticker: str) -> Dict[str, Any]:
        """
        Fetches latest bar data and encapsulates it into a DataEnvelope.
        """
        try:
            request_params = StockLatestBarRequest(symbol_or_symbols=ticker)
            response = self.client.get_stock_latest_bar(request_params)
            
            # Alpaca returns a dict-like object keyed by ticker
            bar = response[ticker]

            return self._create_envelope(
                status="success",
                payload={
                    "ticker": ticker,
                    "price": bar.close,
                    "volume": bar.volume
                },
                metadata={
                    "source_timestamp": bar.timestamp.isoformat(),
                    "confidence_score": 1.0
                }
            )

        except Exception as e:
            return self._create_envelope(
                status="failed",
                payload=None,
                metadata={
                    "error_type": "AUTHENTICATION_FAILURE" if "401" in str(e) else "API_ERROR",
                    "details": str(e)
                }
            )

    def _create_envelope(self, status: str, payload: Optional[Dict], metadata: Dict) -> Dict[str, Any]:
        """
        Internal helper to maintain the Agnostic DataEnvelope structure.
        """
        metadata["status"] = status
        
        return {
            "agent": "AlpacaMarketProvider",
            "type": "MarketData",
            "version": "1.0",
            "producer": "Alpaca-V2",
            "stage": "Data_Retrieval",
            "created_at": datetime.utcnow().isoformat(),
            "payload": payload,
            "metadata": metadata
        }
