# 
# Should you see 'DeprecationWarning: websockets.legacy is deprecated'
# Do this: pip3.14 install --upgrade websockets fastmcp starlette uvicorn
#          pip3.14 install "starlette>=0.40.0,<0.51.0"
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

import uvicorn
from fastapi import FastAPI
from service import MacroService
from routes.http_handler import MCPRouter



from config_api_manager import ConfigApiManager # Your YAML loader

# 1. Setup Configuration and Handlers
config = ConfigApiManager("config_api.yaml")
macro_service = MacroService(config)

# 2. Initialize Service and Handlers
macro_service = MacroService(config)
mcp_sub_app = macro_service.get_app()

# 3. Create your Main Macro-Service App (FastAPI)
app = FastAPI(title="Financial Macro-Service")

# 4. MERGE ROUTES (The Fix)
# This keeps the MCP logic and the REST logic under the same "FastAPI" umbrella
app.mount("/mcp", mcp_sub_app) # Keep MCP in its own sub-path

# 5. Setup your XHR Router
http_router = MCPRouter(macro_service.market)
app.include_router(http_router.router, prefix="/api")

if __name__ == "__main__":
    print("🚀 Macro-service starting on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)