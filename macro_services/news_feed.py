from fastapi import FastAPI, Header, Query
from typing import Optional
from alpaca_news_provider import AlpacaNewsProvider
# requires: pip install alpaca-py

app = FastAPI(title="News Tool Service")

@app.get("/news/{ticker}")
async def fetch_news(
    ticker: str, 
    limit: int = Query(default=5),
    apca_api_key_id: Optional[str] = Header(None, alias="APCA-API-KEY-ID"),
    apca_api_secret_key: Optional[str] = Header(None, alias="APCA-API-SECRET-KEY")
):
    # Pass the keys from headers directly into your provider class
    # This allows the microservice to be 'stateless' regarding credentials
    provider = AlpacaNewsProvider(api_key=apca_api_key_id, api_secret=apca_api_secret_key)
    return provider.get_ticker_news(ticker, limit)
