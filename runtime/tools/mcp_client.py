import asyncio
from mcp import ClientSession
from mcp.client.stdio import stdio_client
# from mcp.client.http import http_client

from runtime.logger import AgentLogger
logger = AgentLogger.get_logger(component="system")


class MCPClient:
    def __init__(self, command: str | None = None, args: list[str] | None = None):
        self.command = command
        self.args = args

        self._session = None
        self._stdio = None
        self._http = None

    # ============================================================================================
    # 1. CONNECTING TO A LOCAL MCP SERVER (PERSISTENT STDIO)
    #
    # client = MCPClient("python", ["tools/mcp/intelligence.py"])
    # await client.connect()
    # tools = await client.list_tools()
    # result = await client.call_tool("search_macro_news", {"query": "Federal Reserve"})
    # await client.close()
    # ============================================================================================
    async def connect(self):
        self._stdio = stdio_client(
            command=self.command,
            args=self.args,
        )
        read, write = await self._stdio.__aenter__()

        self._session = ClientSession(read, write)
        await self._session.__aenter__()
        await self._session.initialize()

    async def list_tools(self):
        return await self._session.list_tools()

    async def call_tool(self, name: str, arguments: dict):
        return await self._session.call_tool(name=name, arguments=arguments)

    async def close(self):
        if self._session:
            await self._session.__aexit__(None, None, None)
        if self._stdio:
            await self._stdio.__aexit__(None, None, None)
        if self._http:
            await self._http.__aexit__(None, None, None)

    # ============================================================================================
    # 2. RESPAWNING MCP SERVER EVERY CALL (ONE-SHOT STDIO)
    #
    # client = MCPClient(command="python", args=["tools/mcp/market.py"])
    # result = await client.call_tool("get_ticker_stats", {"ticker": "AAPL"})
    # ============================================================================================
    async def run(self):
        async with stdio_client(
            command=self.command,
            args=self.args,
        ) as (read, write):

            async with ClientSession(read, write) as session:
                await session.initialize()

                tools = await session.list_tools()
                print("Available tools:")
                for tool in tools.tools:
                    print(f" - {tool.name}: {tool.description}")

                return session

    async def call_tool(self, tool_name: str, arguments: dict):
        async with stdio_client(
            command=self.command,
            args=self.args,
        ) as (read, write):

            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool(
                    name=tool_name,
                    arguments=arguments,
                )

                return result.content

    # ============================================================================================
    # 3. CONNECTING TO A REMOTE MCP SERVER (HTTP / WS)
    #
    # client = MCPClient.remote("http://localhost:3333")
    # tools = await client.list_tools()
    # result = await client.call_tool("search_macro_news", {"query": "Fed"})
    # await client.close()
    # ============================================================================================
    @classmethod
    def remote(cls, endpoint: str) -> "MCPClient":
        client = cls()
        client._http = http_client(endpoint)
        return client

    async def connect_remote(self):
        if not self._http:
            raise RuntimeError("Remote client not initialized. Use MCPClient.remote(url)")

        session = await self._http.__aenter__()
        self._session = session
        await self._session.initialize()
