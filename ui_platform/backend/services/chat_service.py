from sqlalchemy.orm import Session
from models.chat import Message
from models.thread import Thread
from datetime import datetime
from observability.logger import logger


def generate_ai_response(message: str) -> str:
    """
    Replace this with real LLM integration.
    """
    return f"AI Response to: {message}"


def process_chat_message(db: Session, thread_id: str, user_id: str, content: str):
    thread = db.query(Thread).filter(Thread.id == thread_id).first()
    if not thread:
        raise Exception("Thread not found")

    user_message = Message(
        thread_id=thread_id,
        role="user",
        content=content,
        created_at=datetime.utcnow()
    )

    db.add(user_message)
    db.commit()

    ai_content = generate_ai_response(content)

    ai_message = Message(
        thread_id=thread_id,
        role="assistant",
        content=ai_content,
        created_at=datetime.utcnow()
    )

    db.add(ai_message)
    db.commit()

    logger.info(f"Processed chat for thread {thread_id}")

    return ai_message
