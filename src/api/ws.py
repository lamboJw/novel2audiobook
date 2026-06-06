import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.database import SessionLocal
from src.models import Novel

router = APIRouter()


@router.websocket("/ws/progress/{novel_id}")
async def progress_ws(websocket: WebSocket, novel_id: int):
    await websocket.accept()
    try:
        while True:
            db = SessionLocal()
            try:
                novel = db.get(Novel, novel_id)
                if not novel:
                    await websocket.send_json({"error": "not found"})
                    break
                await websocket.send_json({
                    "novel_id": novel.id,
                    "status": novel.status,
                    "title": novel.title,
                })
                if novel.status in ("done", "error"):
                    break
            finally:
                db.close()
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
