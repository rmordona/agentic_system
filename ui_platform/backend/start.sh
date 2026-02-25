AGENTIC_DIR=~/Workspace/ai/projects/agentic_system
export PYTHONPATH=$AGENTIC_DIR:$PYTHONPATH
uvicorn ui_platform.backend.main:app --reload
