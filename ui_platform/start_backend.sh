cd backend

export CORE_ENGINE=/Users/raymondordona/Workspace/ai/projects/agentic_system/core_engine
export MANIFEST_HOME=${CORE_ENGINE}/manifests
uvicorn app.main:app --port 8001  --reload
