from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json

app = FastAPI()

# Serve frontend directory
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# WebSocket clients
clients = set()

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        while True:
            await ws.receive_text()
    except Exception:
        pass
    finally:
        clients.remove(ws)

@app.get("/")
async def index():
    return FileResponse("frontend/index.html")
