from core.paths import WORKSPACES_ROOT

from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Header, Response
from sqlalchemy.orm import Session
from db import get_db
from models.chat import ChatMessage
from models.thread import Thread
from auth.jwt import decode_access_token
from pydantic import BaseModel
from typing import Optional, Dict, Any

from runtime.bootstrap.platform import Platform

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    mode: str = "chat"
    artifacts: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    workspace: str

def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)):
    try:
        token = authorization.split(" ")[1]
        payload = decode_access_token(token)
        return int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/{thread_id}")
async def chat(thread_id: int, 
        req: ChatRequest, 
        response: Response, 
        session_id: Optional[str] = Header(None, alias="X-Session-Id"),
        user_id: int = Depends(get_current_user),
        db: Session = Depends(get_db)):

    print(f"[CHAT REQUEST] Thread: {thread_id}")
    print(f"[CHAT MESSAGE] {req.message}")

    thread = db.query(Thread).filter(Thread.id == thread_id, Thread.owner_id == user_id).first()

    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Save user message
    user_msg = ChatMessage(thread_id=thread.id, role="user", content=req.message)
    db.add(user_msg)
    db.commit()

    # Generate AI response (stub for now, replace with real LLM)
    context = f"Artifacts: {req.artifacts}" if req.mode == "engineering" else ""

    print(f"Session Id: {session_id}")
    print(f"Request Body received: {req}")
    
    workspace_hub = Platform.workspace_hub

    # Get runtime for workspace
    try:
        runtime = await workspace_hub.get_runtime(req.workspace)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Getting runtime for '{req.workspace}' failed: {e}")

    # Run the user message
    try:
        print(f"Workspace here: {req.workspace}")
        result, session_id = await runtime.run_user_message(
            user_id=str(user_id),
            user_intent=req.message,
            session_id=session_id
        )
        print(f"session id from runtime: {session_id}")
        print("but did we get here ...")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent runtime failed: {e}")

    assistant_content = result if isinstance(result, str) else str(result)

    assistant_msg = ChatMessage(thread_id=thread.id, role="assistant", content=assistant_content)
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    response.headers["X-Session-Id"] = session_id

    return {"content": assistant_msg.content}
