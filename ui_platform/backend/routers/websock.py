# routers/websock.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from auth.jwt import decode_access_token
from runtime.bootstrap.platform import Platform

router = APIRouter()


async def get_user_from_token(token: str):
    try:
        payload = decode_access_token(token)
        return int(payload["sub"])
    except Exception:
        return None


@router.websocket("/{thread_id}")
async def chat_ws(
    websocket: WebSocket,
    thread_id: int,
    token: str = Query(...)
):
    await websocket.accept()

    user_id = await get_user_from_token(token)

    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        while True:
            payload = await websocket.receive_json()

            message = payload["message"]
            workspace = payload["workspace"]

            Platform.initialize()
            runtime = Platform.workspace_hub.get_runtime(workspace)

            async for event in runtime.stream_user_message(
                user_id=str(user_id),
                user_intent=message,
                session_id=None,
                verbose=False
            ):
                await websocket.send_json(event)

    except WebSocketDisconnect:
        print(f"Client disconnected (thread {thread_id})")