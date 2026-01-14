# backend/app/api/workspaces_agents.py
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from app.core.config import settings
from typing import List

router = APIRouter()


# dir_path = os.path.dirname(os.path.realpath(__file__).parent.parent)

dir_path = Path(__file__).resolve()
parent_path = dir_path.parent  # one level up
root_folder= settings.ROOT_FOLDER
manifest_home= settings.MANIFEST_HOME
workspace_home=f"{manifest_home}/workspaces"

print(f"Core Engine path: {root_folder}")
print(f"Manifest path: {manifest_home}")
print(f"Workspace path: {workspace_home}")

# Base path to workspaces
WORKSPACES_ROOT = Path(workspace_home)  # <-- change to your actual root path

def list_agent_subfolders(workspace_id: str) -> List[str]:
    """
    Reads the 'agents' subfolder of a workspace and returns the list of agent names.
    Each subfolder is considered an agent.
    """
    agents_dir = WORKSPACES_ROOT / workspace_id / "agents"
    
    if not agents_dir.exists() or not agents_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} or agents folder not found")
    
    # List all subfolders
    agent_names = [p.name for p in agents_dir.iterdir() if p.is_dir()]
    return agent_names

def list_agent_prompt_files(workspace_id: str, agent_name: str) -> List[str]:
    """
    Reads the 'agents' subfolder of a workspace and returns the list of agent names.
    Each subfolder is considered an agent.
    """
    prompts_dir = WORKSPACES_ROOT / workspace_id / "agents" / agent_name / "prompts" 
    
    if not prompts_dir.exists() or not prompts_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} or agents folder not found")
    
    # List all subfolders
    prompt_files = [p.name for p in prompts_dir.iterdir() if p.is_dir()]
    return prompt_files

# Route example
@router.get("/{workspace_id}/agents", response_model=List[str])
async def get_agents(workspace_id: str):
    return list_agent_subfolders(workspace_id)


# -----------------------------
# Get a specific file (prompt.md, skill.json, context.json)
# GET /workspaces/{workspace_id}/agents/{agent_name}/{filename}
# -----------------------------
@router.get("/{workspace_id}/agents/{agent_name}/{filename}")
def get_agent_file(workspace_id: str, agent_name: str, filename: str):
    agent_path = WORKSPACES_ROOT / workspace_id / "agents" / agent_name / filename

    print(f"Request for: {agent_path}")

    if not agent_path.exists():
        raise HTTPException(status_code=404, detail=f"{filename} not found for agent {agent_name}")

    if filename.endswith(".json"):
        import json
        return json.loads(agent_path.read_text())
    else:
        return agent_path.read_text()

