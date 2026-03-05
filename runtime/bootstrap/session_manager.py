import uuid
import time
from dataclasses import dataclass

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(  component="system")

DEFAULT_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days


def _generate_session_id() -> str:
    return str(uuid.uuid4())

class SessionContext(BaseModel):
    # Identifiers
    user_id: str = ""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    # Expiration (derived, never static)
    expires_at: str = Field(
        default_factory=lambda: (
            datetime.utcnow() + timedelta(seconds=DEFAULT_TTL_SECONDS)
        ).isoformat()
    )

    # The Planes
    control_raw: str = "" # The Progressive Plan (artifact.md)
    data_raw: str  = ""   # The Work Body (code.py, contract.docx, etc.)
    
    # Metadata for Agnostic Mapping
    data_type: str = "text" # e.g., 'python', 'markdown', 'json'
    current_stage: str = "initialization"
    
    # Audit Trail
    history: List[str] = []
    metadata: Dict[str, Any] = {}
    
    # Status
    is_complete: bool = False


class SessionManager:
    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.ttl_seconds = ttl_seconds
        # Store active sessions: {session_id: Session}
        self.sessions: dict[str, SessionContext] = {}

    def create_session(self, user_id: str) -> SessionContext:
        now = time.time()
        logger.info(f"Creating new session for user: {user_id}")
        session = SessionContext(
            session_id=_generate_session_id(),
            user_id=user_id
        )
        logger.info(f"New  session for user '{user_id}': {session.session_id}")
        self.sessions[session.session_id] = session
        return session

    def exists(self, user_id: str, session_id: str) -> bool:
        if session_id and session_id in self.sessions:
            session_ctx = self.sessions[session_id]
            if user_id == session_ctx.user_id:
                return True
            else:
                logger.info(f"The user '{user_id}' is using a different session id '{session_ctx.session_id}")
                raise AuthenticationError("Invalid Session detected ...")

    def get(self, session_id: str) -> SessionContext | None:
        return self.sessions[session_id]

    def is_expired(self, session: SessionContext) -> bool:
        return time.time() > session.expires_at

    def delete(self, session_id: str):
        self.sessions.pop(session_id, None)





