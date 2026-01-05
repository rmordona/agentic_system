from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, workspaces, graphs, runs, sse
from app.core.config import settings

#app = FastAPI(title="Agentic UI Platform")

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth")
app.include_router(workspaces.router, prefix="/workspaces")
app.include_router(graphs.router, prefix="/graphs")
app.include_router(runs.router, prefix="/runs")
app.include_router(sse.router, prefix="/events")
