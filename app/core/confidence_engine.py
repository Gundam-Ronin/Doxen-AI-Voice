"""
Phase 7.1 - Confidence Scoring Engine
Reduces wrong assumptions by scoring AI confidence and triggering clarifications.
"""

import os
import json
from typing import Dict, Any, Tuple, List, Optional
from dataclasses import dataclass
from enum import Enum


class ConfidenceLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


@dataclass
class ConfidenceResult:
    score: float
    level: ConfidenceLevel
    needs_clarification: bool
    clarification_prompt: Optional[str]
    reasons: List[str]


class ConfidenceEngine:
    """Scores confidence in extracted data and intent detection."""
    
    def __init__(self):
        self.thresholds = {
            "high": 0.85,
            "medium": 0.65,
            "low": 0.45
        }
        
        self.critical_fields = ["name", "phone", "address", "service_type"]
        
        self.ambiguous_patterns = [
            "maybe", "i think", "probably", "not sure", "i guess",
            "something like", "around", "about", "sort of", "kind of"
        ]
        
        self.confirmation_patterns = [
            "yes", "yeah", "correct", "right", "that's right", "exactly",
            "yep", "sure", "ok", "okay", "sounds good", "perfect"
        ]
    
    def score_extraction(
        self,
        extracted_data: Dict[str, Any],
        transcript: str,
        required_fields: List[str] = None
    ) -> ConfidenceResult:
        """Score confidence in extracted customer data."""
        required = required_fields or self.critical_fields
        reasons = []
        score = 1.0
        
        transcript_lower = transcript.lower()
        for pattern in self.ambiguous_patterns:
            if pattern in transcript_lower:
                score -= 0.1
                reasons.append(f"Ambiguous language detected: '{pattern}'")
        
        missing_critical = []
        for field in required:
            if not extracted_data.get(field):
                missing_critical.append(field)
                score -= 0.15
        
        if missing_critical:
            reasons.append(f"Missing fields: {', '.join(missing_critical)}")
        
        if extracted_data.get("phone"):
            phone = str(extracted_data["phone"]).replace("-", "").replace(" ", "")
            if len(phone) < 10:
                score -= 0.2
                reasons.append("Phone number appears incomplete")
        
        if extracted_data.get("address"):
            addr = extracted_data["address"]
            if len(addr) < 10 or not any(c.isdigit() for c in addr):
                score -= 0.15
                reasons.append("Address may be incomplete (no street number)")
        
        score = max(0.0, min(1.0, score))
        level = self._get_level(score)
        
        needs_clarification = level in [ConfidenceLevel.LOW, ConfidenceLevel.VERY_LOW]
        clarification_prompt = None
        
        if needs_clarification:
            if missing_critical:
                first_missing = missing_critical[0]
                prompts = {
                    "name": "I want to make sure I have your name correct. Could you please tell me your name?",
                    "phone": "Could you please confirm your phone number so we can reach you?",
                    "address": "I need to get your service address. What's the street address where you need service?",
                    "service_type": "What type of service do you need help with today?"
                }
                clarification_prompt = prompts.get(first_missing, f"Could you please confirm your {first_missing}?")
            else:
                clarification_prompt = "I want to make sure I have everything right. Could you repeat that for me?"
        
        return ConfidenceResult(
            score=score,
            level=level,
            needs_clarification=needs_clarification,
            clarification_prompt=clarification_prompt,
            reasons=reasons
        )
    
    def score_intent(
        self,
        intent: str,
        raw_confidence: float,
        transcript: str,
        conversation_context: List[Dict] = None
    ) -> ConfidenceResult:
        """Score confidence in detected intent."""
        reasons = []
        score = raw_confidence
        
        transcript_lower = transcript.lower()
        word_count = len(transcript.split())
        
        if word_count < 3:
            score -= 0.15
            reasons.append("Very short utterance - may be incomplete")
        
        if "?" in transcript:
            if intent in ["BOOK_APPOINTMENT", "CONFIRMATION"]:
                score -= 0.2
                reasons.append("Question mark suggests inquiry, not commitment")
        
        if intent == "CONFIRMATION":
            has_confirmation = any(p in transcript_lower for p in self.confirmation_patterns)
            if not has_confirmation:
                score -= 0.25
                reasons.append("No clear confirmation words detected")
        
        if conversation_context:
            recent_intents = [c.get("intent") for c in conversation_context[-3:] if c.get("intent")]
            if intent in recent_intents:
                score += 0.05
                reasons.append("Consistent with recent conversation flow")
        
        score = max(0.0, min(1.0, score))
        level = self._get_level(score)
        
        needs_clarification = level == ConfidenceLevel.VERY_LOW
        clarification_prompt = None
        
        if needs_clarification:
            prompts = {
                "BOOK_APPOINTMENT": "Just to confirm - would you like me to schedule an appointment for you?",
                "EMERGENCY": "This sounds urgent. Should I dispatch a technician right away?",
                "CONFIRMATION": "I want to make sure - is that a yes to confirm?",
                "CANCEL": "Are you sure you want to cancel?"
            }
            clarification_prompt = prompts.get(intent, "Could you tell me more about what you need?")
        
        return ConfidenceResult(
            score=score,
            level=level,
            needs_clarification=needs_clarification,
            clarification_prompt=clarification_prompt,
            reasons=reasons
        )
    
    def should_repeat_back(
        self,
        data_type: str,
        value: Any,
        confidence: float
    ) -> Tuple[bool, Optional[str]]:
        """Determine if a value should be repeated back for confirmation."""
        if confidence >= self.thresholds["high"]:
            return False, None
        
        repeat_templates = {
            "name": f"I have your name as {value}. Is that correct?",
            "phone": f"Let me confirm your phone number: {value}. Is that right?",
            "address": f"Your service address is {value}. Did I get that correct?",
            "appointment_time": f"I have you down for {value}. Does that work for you?",
            "service_type": f"You're looking for help with {value}. Is that correct?"
        }
        
        if data_type in repeat_templates:
            return True, repeat_templates[data_type]
        
        return True, f"I have {value} for your {data_type}. Is that correct?"
    
    def validate_date_understanding(
        self,
        spoken_date: str,
        parsed_date: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate date parsing and suggest correction if needed."""
        today_refs = ["today", "now", "right now", "immediately"]
        tomorrow_refs = ["tomorrow", "next day"]
        
        spoken_lower = spoken_date.lower()
        
        needs_correction = False
        correction = None
        
        if any(ref in spoken_lower for ref in today_refs):
            if "today" not in parsed_date.lower():
                needs_correction = True
                correction = f"Just to clarify - did you mean today, {parsed_date}?"
        
        ordinal_patterns = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th",
                          "10th", "11th", "12th", "13th", "14th", "15th", "16th", "17th",
                          "18th", "19th", "20th", "21st", "22nd", "23rd", "24th", "25th",
                          "26th", "27th", "28th", "29th", "30th", "31st"]
        
        for ordinal in ordinal_patterns:
            if ordinal in spoken_lower:
                if ordinal not in parsed_date.lower():
                    needs_correction = True
                    correction = f"Did you mean the {ordinal}? I have {parsed_date}."
                break
        
        return needs_correction, correction
    
    def _get_level(self, score: float) -> ConfidenceLevel:
        """Convert numeric score to confidence level."""
        if score >= self.thresholds["high"]:
            return ConfidenceLevel.HIGH
        elif score >= self.thresholds["medium"]:
            return ConfidenceLevel.MEDIUM
        elif score >= self.thresholds["low"]:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW


confidence_engine = ConfidenceEngine()
