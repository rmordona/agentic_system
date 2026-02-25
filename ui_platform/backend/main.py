
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import auth, chat, threads, observability, websock
import uvicorn

from runtime.bootstrap.platform import Platform

app = FastAPI(title="Context Engineering Platform Backend")

@app.on_event("startup")
async def startup_event():
    Platform.initialize()

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(websock.router, prefix="/api/v1/ws", tags=["websock"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(threads.router, prefix="/api/v1/threads", tags=["threads"])
app.include_router(observability.router, prefix="/api/v1/observability", tags=["observability"])

@app.get("/")
def root():
    return {"status": "Context Engineering Platform Backend Running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)




