import asyncio
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database.session import get_db
from ..database.models import ActiveCall
from ..core.call_manager import call_manager

router = APIRouter(prefix="/api/stream", tags=["streaming"])

@router.get("/transcripts/{business_id}")
async def stream_transcripts(business_id: int):
    async def event_generator():
        queue = call_manager.subscribe_to_transcripts(business_id)
        
        yield f"data: {json.dumps({'type': 'connected', 'message': 'Stream connected'})}\n\n"
        
        try:
            while True:
                try:
                    entry = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    event_data = {
                        "type": "transcript",
                        "speaker": entry.get("speaker", ""),
                        "text": entry.get("text", ""),
                        "timestamp": entry.get("timestamp", "")
                    }
                    
                    yield f"data: {json.dumps(event_data)}\n\n"
                    
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                    
        except asyncio.CancelledError:
            call_manager.unsubscribe_from_transcripts(business_id)
            raise
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*"
        }
    )

@router.get("/active-calls/{business_id}")
async def get_active_calls(business_id: int, db: Session = Depends(get_db)):
    active_calls = db.query(ActiveCall).filter(
        ActiveCall.business_id == business_id,
        ActiveCall.status == "in_progress"
    ).all()
    
    memory_calls = call_manager.get_active_calls_for_business(business_id)
    
    calls = []
    for call in active_calls:
        memory_call = next(
            (c for c in memory_calls if c["call_sid"] == call.call_sid),
            None
        )
        
        calls.append({
            "call_sid": call.call_sid,
            "caller_number": call.caller_number,
            "started_at": call.started_at.isoformat() if call.started_at else None,
            "transcript": memory_call.get("transcript", []) if memory_call else []
        })
    
    return {"active_calls": calls}

@router.get("/call-transcript/{call_sid}")
async def get_call_transcript(call_sid: str):
    call_data = call_manager.get_call(call_sid)
    
    if not call_data:
        return {"transcript": [], "status": "not_found"}
    
    return {
        "call_sid": call_sid,
        "status": call_data.get("status", "unknown"),
        "transcript": call_data.get("transcript", []),
        "started_at": call_data.get("started_at").isoformat() if call_data.get("started_at") else None
    }
