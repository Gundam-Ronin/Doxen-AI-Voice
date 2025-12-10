import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from collections import defaultdict

active_calls: Dict[str, Dict[str, Any]] = {}
transcript_queues: Dict[int, asyncio.Queue] = defaultdict(asyncio.Queue)

class CallManager:
    def __init__(self):
        self.calls = active_calls
        self.queues = transcript_queues
    
    def start_call(self, call_sid: str, business_id: int, caller_number: str) -> Dict[str, Any]:
        call_data = {
            "call_sid": call_sid,
            "business_id": business_id,
            "caller_number": caller_number,
            "started_at": datetime.utcnow(),
            "transcript": [],
            "conversation_history": [],
            "status": "in_progress"
        }
        self.calls[call_sid] = call_data
        return call_data
    
    def add_transcript(self, call_sid: str, speaker: str, text: str):
        if call_sid in self.calls:
            entry = {
                "speaker": speaker,
                "text": text,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.calls[call_sid]["transcript"].append(entry)
            self.calls[call_sid]["conversation_history"].append({
                "role": "user" if speaker == "customer" else "assistant",
                "content": text
            })
            
            business_id = self.calls[call_sid]["business_id"]
            asyncio.create_task(self._push_to_queue(business_id, entry))
    
    async def _push_to_queue(self, business_id: int, entry: Dict[str, Any]):
        if business_id in self.queues:
            await self.queues[business_id].put(entry)
    
    def get_call(self, call_sid: str) -> Optional[Dict[str, Any]]:
        return self.calls.get(call_sid)
    
    def get_conversation_history(self, call_sid: str) -> list:
        if call_sid in self.calls:
            return self.calls[call_sid]["conversation_history"]
        return []
    
    def end_call(self, call_sid: str) -> Optional[Dict[str, Any]]:
        if call_sid in self.calls:
            self.calls[call_sid]["status"] = "completed"
            self.calls[call_sid]["ended_at"] = datetime.utcnow()
            return self.calls.pop(call_sid)
        return None
    
    def get_active_calls_for_business(self, business_id: int) -> list:
        return [
            call for call in self.calls.values()
            if call["business_id"] == business_id and call["status"] == "in_progress"
        ]
    
    def subscribe_to_transcripts(self, business_id: int) -> asyncio.Queue:
        if business_id not in self.queues:
            self.queues[business_id] = asyncio.Queue()
        return self.queues[business_id]
    
    def unsubscribe_from_transcripts(self, business_id: int):
        if business_id in self.queues:
            del self.queues[business_id]

call_manager = CallManager()
