from fastmcp import FastMCP
from handlers.market_handler import MarketHandler
from handlers.ticker_handler import TickerHandler

class MacroService:
    def __init__(self, config):
        # 1. Initialize the MCP Server
        self.mcp = FastMCP("Financial-Macro-Service")

        # This will print all methods that look like 'app'
        print([method for method in dir(self.mcp) if 'app' in method])
        
        # 2. Instantiate your Handlers (Isolating the logic)
        self.market = MarketHandler(config.api_key, config.api_secret)
        self.ticker = TickerHandler()
        
        # 3. Register the tools
        self._register_mcp_tools()

    def _register_mcp_tools(self):
        """
        All tool definitions are wrapped here to keep the __init__ clean.
        """
        
        @self.mcp.tool()
        async def get_market_data(intent: str):
            """Identify a company from a natural language query and fetch its market data."""
            # Ask the TickerHandler to turn "The iPhone maker" into "AAPL"
            ticker = await self.ticker.resolve(intent)
            
            if not ticker:
                return "I couldn't identify a specific stock ticker in your request."
            
            # Pass the clean ticker to the MarketHandler
            return await self.market.fetch_data(ticker)

        @self.mcp.tool()
        async def get_ticker_news(intent: str):
            """Identify a company and fetch the latest relevant news."""
            ticker = await self.ticker.resolve(intent)
            
            if not ticker:
                return "I couldn't identify a specific stock ticker to find news for."
                
            return await self.market.fetch_news(ticker)

    def get_app(self):
        # In FastMCP 3.0, this handles SSE and standard HTTP together
        return self.mcp.http_app()