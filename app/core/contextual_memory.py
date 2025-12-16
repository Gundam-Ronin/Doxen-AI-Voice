"""
Phase 7.1 - Contextual Memory Engine
Maintains conversation context and customer history across the call session.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import json


@dataclass
class MemoryEntry:
    timestamp: datetime
    entry_type: str
    content: Dict[str, Any]
    confidence: float = 1.0
    source: str = "conversation"


@dataclass
class ConversationSlot:
    """A slot in the conversation state machine."""
    name: str
    value: Any = None
    confirmed: bool = False
    attempts: int = 0
    last_asked: Optional[datetime] = None


class ContextualMemory:
    """Maintains rich context throughout a call session."""
    
    def __init__(self, max_history: int = 50):
        self.max_history = max_history
        self.session_id: Optional[str] = None
        self.business_id: Optional[int] = None
        self.customer_id: Optional[int] = None
        
        self.transcript_history: deque = deque(maxlen=max_history)
        self.intent_history: List[MemoryEntry] = []
        self.extraction_history: List[MemoryEntry] = []
        
        self.slots: Dict[str, ConversationSlot] = {
            "name": ConversationSlot(name="name"),
            "phone": ConversationSlot(name="phone"),
            "email": ConversationSlot(name="email"),
            "address": ConversationSlot(name="address"),
            "service_type": ConversationSlot(name="service_type"),
            "preferred_date": ConversationSlot(name="preferred_date"),
            "preferred_time": ConversationSlot(name="preferred_time"),
            "urgency": ConversationSlot(name="urgency"),
        }
        
        self.conversation_state = "greeting"
        self.booking_state: Optional[str] = None
        
        self.customer_profile: Dict[str, Any] = {}
        
        self.call_metadata: Dict[str, Any] = {
            "start_time": None,
            "language": "en",
            "sentiment_trend": [],
            "topic_changes": 0,
            "clarifications_requested": 0,
        }
        
        self.pending_confirmations: List[Dict] = []
    
    def start_session(
        self,
        session_id: str,
        business_id: int,
        caller_phone: str = None,
        customer_data: Dict = None
    ):
        """Initialize a new call session."""
        self.session_id = session_id
        self.business_id = business_id
        self.call_metadata["start_time"] = datetime.utcnow()
        
        if caller_phone:
            self.set_slot("phone", caller_phone, confirmed=True)
        
        if customer_data:
            self.customer_profile = customer_data
            if customer_data.get("name"):
                self.set_slot("name", customer_data["name"], confirmed=True)
            if customer_data.get("address"):
                self.set_slot("address", customer_data["address"], confirmed=False)
    
    def add_transcript(self, speaker: str, text: str, timestamp: datetime = None):
        """Add a transcript entry to history."""
        entry = {
            "speaker": speaker,
            "text": text,
            "timestamp": timestamp or datetime.utcnow()
        }
        self.transcript_history.append(entry)
    
    def add_intent(self, intent: str, confidence: float, metadata: Dict = None):
        """Record a detected intent."""
        entry = MemoryEntry(
            timestamp=datetime.utcnow(),
            entry_type="intent",
            content={
                "intent": intent,
                "metadata": metadata or {}
            },
            confidence=confidence
        )
        self.intent_history.append(entry)
        
        if len(self.intent_history) > 2:
            prev_intent = self.intent_history[-2].content.get("intent")
            if prev_intent and prev_intent != intent:
                self.call_metadata["topic_changes"] += 1
    
    def add_extraction(self, field: str, value: Any, confidence: float):
        """Record an extracted field."""
        entry = MemoryEntry(
            timestamp=datetime.utcnow(),
            entry_type="extraction",
            content={"field": field, "value": value},
            confidence=confidence
        )
        self.extraction_history.append(entry)
        
        if confidence >= 0.7:
            self.set_slot(field, value, confirmed=(confidence >= 0.85))
    
    def set_slot(self, slot_name: str, value: Any, confirmed: bool = False):
        """Set a conversation slot value."""
        if slot_name in self.slots:
            slot = self.slots[slot_name]
            slot.value = value
            slot.confirmed = confirmed
            slot.attempts += 1
        else:
            self.slots[slot_name] = ConversationSlot(
                name=slot_name,
                value=value,
                confirmed=confirmed,
                attempts=1
            )
    
    def get_slot(self, slot_name: str) -> Optional[Any]:
        """Get a slot value."""
        slot = self.slots.get(slot_name)
        return slot.value if slot else None
    
    def is_slot_confirmed(self, slot_name: str) -> bool:
        """Check if a slot is confirmed."""
        slot = self.slots.get(slot_name)
        return slot.confirmed if slot else False
    
    def get_missing_slots(self, required: List[str] = None) -> List[str]:
        """Get list of missing required slots."""
        required = required or ["name", "phone", "address", "service_type"]
        missing = []
        for slot_name in required:
            slot = self.slots.get(slot_name)
            if not slot or not slot.value:
                missing.append(slot_name)
        return missing
    
    def get_unconfirmed_slots(self) -> List[str]:
        """Get slots that have values but aren't confirmed."""
        return [
            name for name, slot in self.slots.items()
            if slot.value and not slot.confirmed
        ]
    
    def get_next_slot_to_fill(self, priority_order: List[str] = None) -> Optional[str]:
        """Get the next slot that needs to be filled or confirmed."""
        priority = priority_order or ["name", "phone", "address", "service_type", "preferred_date"]
        
        for slot_name in priority:
            slot = self.slots.get(slot_name)
            if not slot or not slot.value:
                if not slot:
                    self.slots[slot_name] = ConversationSlot(name=slot_name)
                return slot_name
        
        for slot_name in priority:
            slot = self.slots.get(slot_name)
            if slot and slot.value and not slot.confirmed:
                return slot_name
        
        return None
    
    def get_slot_prompt(self, slot_name: str) -> str:
        """Get the prompt to ask for a slot."""
        prompts = {
            "name": "May I have your name, please?",
            "phone": "What's the best phone number to reach you?",
            "email": "Would you like to provide an email for confirmation?",
            "address": "What's the address where you need service?",
            "service_type": "What type of service do you need today?",
            "preferred_date": "What day works best for you?",
            "preferred_time": "Do you prefer morning or afternoon?",
            "urgency": "Is this urgent, or can it wait a few days?",
        }
        return prompts.get(slot_name, f"Could you provide your {slot_name}?")
    
    def get_confirmation_prompt(self, slot_name: str) -> str:
        """Get the prompt to confirm a slot value."""
        slot = self.slots.get(slot_name)
        if not slot or not slot.value:
            return self.get_slot_prompt(slot_name)
        
        templates = {
            "name": f"I have your name as {slot.value}. Is that correct?",
            "phone": f"Your phone number is {slot.value}. Is that right?",
            "address": f"Your service address is {slot.value}. Did I get that correct?",
            "service_type": f"You need help with {slot.value}. Is that correct?",
            "preferred_date": f"You'd like an appointment on {slot.value}. Does that work?",
        }
        return templates.get(slot_name, f"I have {slot.value} for {slot_name}. Is that correct?")
    
    def get_recent_context(self, turns: int = 5) -> List[Dict]:
        """Get recent conversation turns for context."""
        recent = list(self.transcript_history)[-turns:]
        return [
            {"role": t["speaker"], "content": t["text"]}
            for t in recent
        ]
    
    def get_dominant_intent(self) -> Optional[str]:
        """Get the most frequently detected intent in this session."""
        if not self.intent_history:
            return None
        
        intent_counts: Dict[str, float] = {}
        for entry in self.intent_history:
            intent = entry.content.get("intent")
            if intent:
                intent_counts[intent] = intent_counts.get(intent, 0) + entry.confidence
        
        if intent_counts:
            return max(intent_counts, key=intent_counts.get)
        return None
    
    def record_sentiment(self, sentiment: str):
        """Track sentiment throughout the call."""
        self.call_metadata["sentiment_trend"].append({
            "sentiment": sentiment,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def get_sentiment_trend(self) -> str:
        """Analyze overall sentiment trend."""
        trends = self.call_metadata.get("sentiment_trend", [])
        if not trends:
            return "neutral"
        
        sentiment_scores = {"positive": 1, "neutral": 0, "negative": -1}
        total = sum(sentiment_scores.get(t["sentiment"], 0) for t in trends)
        avg = total / len(trends) if trends else 0
        
        if avg > 0.3:
            return "positive"
        elif avg < -0.3:
            return "negative"
        return "neutral"
    
    def add_pending_confirmation(self, field: str, value: Any):
        """Queue a value for confirmation."""
        self.pending_confirmations.append({
            "field": field,
            "value": value,
            "added_at": datetime.utcnow()
        })
    
    def get_pending_confirmation(self) -> Optional[Dict]:
        """Get next pending confirmation."""
        if self.pending_confirmations:
            return self.pending_confirmations[0]
        return None
    
    def confirm_pending(self, confirmed: bool = True):
        """Confirm or reject the pending confirmation."""
        if self.pending_confirmations:
            pending = self.pending_confirmations.pop(0)
            if confirmed:
                self.set_slot(pending["field"], pending["value"], confirmed=True)
    
    def to_summary(self) -> Dict[str, Any]:
        """Generate a summary of the conversation."""
        return {
            "session_id": self.session_id,
            "duration_seconds": (datetime.utcnow() - self.call_metadata["start_time"]).total_seconds() if self.call_metadata["start_time"] else 0,
            "slots_filled": {name: slot.value for name, slot in self.slots.items() if slot.value},
            "slots_confirmed": {name: slot.confirmed for name, slot in self.slots.items() if slot.value},
            "dominant_intent": self.get_dominant_intent(),
            "sentiment_trend": self.get_sentiment_trend(),
            "topic_changes": self.call_metadata["topic_changes"],
            "clarifications": self.call_metadata["clarifications_requested"],
            "transcript_count": len(self.transcript_history),
        }
    
    def reset(self):
        """Reset memory for a new call."""
        self.session_id = None
        self.business_id = None
        self.customer_id = None
        self.transcript_history.clear()
        self.intent_history.clear()
        self.extraction_history.clear()
        self.slots = {
            "name": ConversationSlot(name="name"),
            "phone": ConversationSlot(name="phone"),
            "email": ConversationSlot(name="email"),
            "address": ConversationSlot(name="address"),
            "service_type": ConversationSlot(name="service_type"),
            "preferred_date": ConversationSlot(name="preferred_date"),
            "preferred_time": ConversationSlot(name="preferred_time"),
            "urgency": ConversationSlot(name="urgency"),
        }
        self.conversation_state = "greeting"
        self.booking_state = None
        self.customer_profile = {}
        self.call_metadata = {
            "start_time": None,
            "language": "en",
            "sentiment_trend": [],
            "topic_changes": 0,
            "clarifications_requested": 0,
        }
        self.pending_confirmations = []


contextual_memory = ContextualMemory()
