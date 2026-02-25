from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db import get_db
from auth.jwt import decode_access_token
from fastapi import Header, Path

from models.thread import Thread
from models.chat import ChatMessage
from models.user import User


router = APIRouter()

def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)):
    try:
        token = authorization.split(" ")[1]
        payload = decode_access_token(token)
        return int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/", summary="Get all threads")
def get_threads(user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    threads = db.query(Thread).filter(Thread.owner_id == user_id).all()
    return [{"id": t.id, "title": t.title} for t in threads]

@router.post("/", summary="Create a thread")
def create_thread(title: str, user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    thread = Thread(title=title, owner_id=user_id)
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return {"id": thread.id, "title": thread.title}


@router.get("/{thread_id}/messages", summary="Get messages for a thread")
def get_thread_messages(
    thread_id: int = Path(..., description="The ID of the thread"),
    user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Ensure the thread belongs to the user
    thread = db.query(Thread).filter(Thread.id == thread_id, Thread.owner_id == user_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    messages = db.query(ChatMessage).filter(ChatMessage.thread_id == thread_id).order_by(ChatMessage.created_at).all()
    return [
        {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at}
        for m in messages
    ]
