from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from db import SessionLocal
from models.chat import ChatMessage
from models.thread import Thread
import asyncio

router = APIRouter()

@router.websocket("/ws/chat/{thread_id}")
async def chat_ws(websocket: WebSocket, thread_id: int):
    await websocket.accept()
    db: Session = SessionLocal()
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")

            # Save user message
            user_msg = ChatMessage(thread_id=thread_id, role="user", content=message)
            db.add(user_msg)
            db.commit()

            # Simulate streaming AI response
            response = f"Streaming response to: {message}"
            for chunk in response.split(" "):
                await websocket.send_text(chunk + " ")
                await asyncio.sleep(0.2)  # streaming delay

            assistant_msg = ChatMessage(thread_id=thread_id, role="assistant", content=response)
            db.add(assistant_msg)
            db.commit()
    except WebSocketDisconnect:
        print("Client disconnected")
    finally:
        db.close()
