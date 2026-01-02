from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import Optional
from runtime.singleton_resources import SingletonResources
from runtime.runtime_factory import get_runtime

app = FastAPI()
session_control = SingletonResources.session_control  # singleton instance

# ----------------------------
# Request Schema
# ----------------------------
class RunTaskRequest(BaseModel):
    task: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None

# ----------------------------
# Response Schema
# ----------------------------
class RunTaskResponse(BaseModel):
    session_id: str
    task: str
    result: dict

@app.post("/run_task", response_model=RunTaskResponse)
async def run_task(req: RunTaskRequest):
    try:
        user_id = req.user_id
        session_id = req.session_id

        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")

        # 1️⃣ Resolve or create session
        if session_id:
            session = session_control.get(session_id)
            if session is None or session_control.is_expired(session):
                # Session missing or expired → create new
                session = session_control.create_session(user_id)
        else:
            # No session_id provided → create new session
            session = session_control.create_session(user_id)

        # Optional: cleanup expired sessions periodically
        expired_sessions = [
            sid for sid, s in session_control.sessions.items() if session_control.is_expired(s)
        ]
        for sid in expired_sessions:
            session_control.delete(sid)

        # 2️⃣ Pass session info to Runtime
        runtime = get_runtime(session_id=session.session_id, user_id=session.user_id)

        # 3️⃣ Run task
        result = await runtime.run(req.task)

        return RunTaskResponse(
            session_id=session.session_id,
            task=req.task,
            result=result
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
