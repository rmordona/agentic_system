############################################################################
# FULL STREAM + RESUME SEQUENCE
#
#    Frontend (Browser)
#            │
#            │ 1. User sends initial message
#            ▼
#    websocket_chat()
#            │
#            │ 2. runtime.stream_user_message(...)
#            ▼
#    RuntimeManager
#            │
#            │ 3. get_orchestrator(session_id)
#            ▼
#    Orchestrator.run_stream()
#            │
#            │ 4. self._graph.astream(initial_state, config)
#            ▼
#    LangGraph
#            │
#            │ 5. planner → runner → validator → hitl
#            ▼
#    AgentHITL.__call__()
#            │
#            │ 6. interrupt({...})
#           │     ├─ MemorySaver stores checkpoint under thread_id
#            │     └─ Graph execution PAUSES here
#            ▼
#    LangGraph emits "__interrupt__" event
#            │
#            ▼
#    Orchestrator yields event
#            │
#            ▼
#    websocket_chat sends event to frontend
#            │
#            ▼
#    Frontend displays HITL prompt
#
############################################################################
# USER RESPONDS
#
#    Frontend
#            │
#            │ 7. User submits HITL approval
#            ▼
#    websocket_chat()
#            │
#            │ 8. runtime.resume_stream(human_input, session_id)
#            ▼
#    RuntimeManager
#            │
#            │ 9. get_orchestrator(session_id)  (same object)
#            ▼
#    Orchestrator.resume_stream()
#            │
#            │ 10. self._graph.astream(
#            │        Command(resume=human_input),
#            │        same config(thread_id)
#            │    )
#            ▼
#    LangGraph
#            │
#            │ 11. MemorySaver loads checkpoint for thread_id
#            │
#            │ 12. Execution resumes EXACTLY at interrupt()
#            ▼
#    AgentHITL.__call__(state)
#            │
#            │ state.human_response == human_input
#            │
#            │ 13. returns:
#            │      {"hitl_completed": True, "approved": ...}
#            ▼
#    LangGraph continues graph execution
#            │
#            │ planner → runner → validator → ...
#            ▼
#    Events streamed back up
#            ▼
#    Orchestrator yields
#            ▼
#    websocket_chat sends to frontend
#            ▼
#    Frontend updates UI
#
############################################################################

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session
from db import get_db
from models.thread import Thread
from models.chat import ChatMessage
from auth.jwt import decode_access_token
from langgraph.types import Command


from runtime.bootstrap.platform import Platform
from runtime.logger import AgentLogger

logger = AgentLogger.get_logger(component="system")

router = APIRouter()

async def handle_graph_stream(
    websocket: WebSocket,
    stream,
    thread: Thread,
    db: Session,
):
    """
    Handles LangGraph streaming lifecycle:
    - interrupt handling (multi)
    - token streaming
    - session updates
    - assistant persistence
    """

    full_response = ""
    updated_session_id = thread.session_id
    interrupted = False

    async for event in stream:

        logger.info(f"Handle saw event: {event}")
        print("Handler saw event: ", event)

        if isinstance(event, dict) and "type" in event:
            if event.get("type") == "event":
                event = event.get("event")

        # --------------------------------------------------
        # Handle Interrupt(s)
        # --------------------------------------------------
        if isinstance(event, dict) and "__interrupt__" in event:
            interrupts = event.get("__interrupt__", [])

            if not isinstance(interrupts, list):
                interrupts = [interrupts]

            logger.info(f"Interrupt caught: {interrupts}")

            for payload in interrupts:
                if not isinstance(payload, dict):
                    continue

                await websocket.send_json({
                    "type": "hitl_required",
                    **payload
                })

            interrupted = True
            break  # stop consuming stream immediately

        # --------------------------------------------------
        # Capture session updates
        # --------------------------------------------------
        if isinstance(event, dict) and event.get("type") == "session_update":
            updated_session_id = event["session_id"]

            logger.info(f"Session Update: {updated_session_id}")
            # Persist immediately
            if updated_session_id != thread.session_id:
                thread.session_id = updated_session_id
                db.commit()
            logger.info(f"Session Update Completed ...")
            continue

        # --------------------------------------------------
        # Token streaming
        # --------------------------------------------------
        if isinstance(event, str):
            full_response += event

            await websocket.send_json({
                "type": "token",
                "content": event
            })

        # --------------------------------------------------
        # Structured event streaming
        # --------------------------------------------------
        else:
            await websocket.send_json({
                "type": "event",
                "event": event
            })

    # ==================================================
    # FINALIZATION (only if NOT interrupted)
    # ==================================================
    if not interrupted:

        # Persist assistant message
        if full_response.strip():
            assistant_msg = ChatMessage(
                thread_id=thread.id,
                role="assistant",
                content=full_response
            )
            db.add(assistant_msg)
            db.commit()

        await websocket.send_json({
            "type": "completion"
        })



@router.websocket("/{thread_id}")
async def websocket_chat(websocket: WebSocket, thread_id: int):
    await websocket.accept()

    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    db: Session = next(get_db())

    try:
        thread: Thread | None = db.query(Thread).filter(
            Thread.id == thread_id,
            Thread.owner_id == user_id
        ).first()

        if not thread:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        workspace_hub = Platform.workspace_hub

        while True:

            raw = await websocket.receive_text()
            data = json.loads(raw)

            msg_type = data.get("type", "user_message")
            workspace = data.get("workspace")

            if not workspace:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return

            runtime = await workspace_hub.get_runtime(workspace)
            session_id = thread.session_id

            # ==============================================
            # USER MESSAGE
            # ==============================================
            if msg_type == "user_message":

                message = data.get("message")
                if not message:
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                    return

                # Persist user message
                db.add(ChatMessage(
                    thread_id=thread.id,
                    role="user",
                    content=message
                ))
                db.commit()

                stream = runtime.run_stream(
                    user_id=str(user_id),
                    user_intent=message,
                    session_id=session_id,
                )

            # ==============================================
            # HITL RESUME
            # ==============================================
            elif msg_type == "hitl_response":

                human_input = data.get("content")
                if human_input is None:
                    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                    return

                stream = runtime.resume_stream(
                    human_input=human_input,
                    session_id=session_id,
                )

            else:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return

            # ==============================================
            # Delegate ALL streaming lifecycle
            # ==============================================
            await handle_graph_stream(
                websocket=websocket,
                stream=stream,
                thread=thread,
                db=db,
            )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")

    except Exception:
        logger.exception("Unexpected WS error")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)

    finally:
        db.close()