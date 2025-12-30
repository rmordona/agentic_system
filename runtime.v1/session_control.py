import uuid
import time
from dataclasses import dataclass

DEFAULT_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days

@dataclass
class Session:
    session_id: str
    user_id: str
    created_at: float
    expires_at: float


class SessionControl:
    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.ttl_seconds = ttl_seconds
        # Store active sessions: {session_id: Session}
        self.sessions: dict[str, Session] = {}

    def create_session(self, user_id: str) -> Session:
        now = time.time()
        session = Session(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            created_at=now,
            expires_at=now + self.ttl_seconds,
        )
        self.sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        return self.sessions.get(session_id)

    def is_expired(self, session: Session) -> bool:
        return time.time() > session.expires_at

    def delete(self, session_id: str):
        self.sessions.pop(session_id, None)




