"""
Phase 7.1 - Fallback Decision Tree Engine
Handles confusing questions with structured fallback responses.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class FallbackType(Enum):
    CLARIFICATION = "clarification"
    REPHRASE = "rephrase"
    OFFER_ALTERNATIVES = "offer_alternatives"
    ESCALATE_HUMAN = "escalate_human"
    CALLBACK_OFFER = "callback_offer"
    KNOWLEDGE_GAP = "knowledge_gap"


@dataclass
class FallbackAction:
    fallback_type: FallbackType
    response: str
    follow_up_question: Optional[str]
    should_log: bool = True
    priority: int = 1


class FallbackNode:
    """A node in the fallback decision tree."""
    
    def __init__(
        self,
        condition: str,
        action: FallbackAction,
        children: List['FallbackNode'] = None
    ):
        self.condition = condition
        self.action = action
        self.children = children or []


class FallbackEngine:
    """Decision tree engine for handling confusing or unanswerable situations."""
    
    def __init__(self):
        self.confusion_indicators = [
            "what do you mean", "i don't understand", "huh", "what",
            "can you repeat", "say that again", "confused", "sorry what",
            "pardon", "excuse me", "come again"
        ]
        
        self.frustration_indicators = [
            "this is ridiculous", "talk to a human", "real person",
            "i need help", "this isn't working", "frustrated",
            "can't understand", "stupid", "useless"
        ]
        
        self.off_topic_indicators = [
            "weather", "sports", "news", "joke", "sing", "play music",
            "what time is it", "who are you", "are you real", "are you a robot"
        ]
        
        self.pricing_blockers = [
            "exact price", "exact cost", "guarantee price", "final quote",
            "lock in price", "price match"
        ]
        
        self.confusion_count = 0
        self.max_confusions = 3
    
    def evaluate(
        self,
        transcript: str,
        context: Dict[str, Any],
        last_ai_response: str = None
    ) -> Optional[FallbackAction]:
        """Evaluate transcript and return appropriate fallback action if needed."""
        transcript_lower = transcript.lower()
        
        if self._is_confused(transcript_lower):
            self.confusion_count += 1
            return self._handle_confusion(context, last_ai_response)
        
        if self._is_frustrated(transcript_lower):
            return self._handle_frustration(context)
        
        if self._is_off_topic(transcript_lower):
            return self._handle_off_topic(transcript_lower, context)
        
        if self._is_pricing_request(transcript_lower):
            return self._handle_pricing_blocker(context)
        
        if self._is_knowledge_gap(transcript_lower, context):
            return self._handle_knowledge_gap(context)
        
        self.confusion_count = 0
        return None
    
    def _is_confused(self, transcript: str) -> bool:
        return any(ind in transcript for ind in self.confusion_indicators)
    
    def _is_frustrated(self, transcript: str) -> bool:
        return any(ind in transcript for ind in self.frustration_indicators)
    
    def _is_off_topic(self, transcript: str) -> bool:
        return any(ind in transcript for ind in self.off_topic_indicators)
    
    def _is_pricing_request(self, transcript: str) -> bool:
        return any(ind in transcript for ind in self.pricing_blockers)
    
    def _is_knowledge_gap(self, transcript: str, context: Dict) -> bool:
        gap_indicators = [
            "do you do", "can you help with", "do you offer",
            "what about", "is there", "do you have"
        ]
        return any(ind in transcript for ind in gap_indicators)
    
    def _handle_confusion(self, context: Dict, last_response: str) -> FallbackAction:
        if self.confusion_count >= self.max_confusions:
            return FallbackAction(
                fallback_type=FallbackType.ESCALATE_HUMAN,
                response="I apologize for the confusion. Let me connect you with one of our team members who can better assist you. Would you prefer a callback, or would you like to hold?",
                follow_up_question=None,
                priority=3
            )
        
        if self.confusion_count == 2:
            return FallbackAction(
                fallback_type=FallbackType.REPHRASE,
                response="Let me try to explain that differently. What I need to help you is your name, phone number, and what service you need. Can you start with your name?",
                follow_up_question="What is your name?",
                priority=2
            )
        
        return FallbackAction(
            fallback_type=FallbackType.CLARIFICATION,
            response="I'm sorry, let me clarify. How can I help you today? Are you looking to schedule a service appointment?",
            follow_up_question="Would you like to schedule an appointment?",
            priority=1
        )
    
    def _handle_frustration(self, context: Dict) -> FallbackAction:
        return FallbackAction(
            fallback_type=FallbackType.ESCALATE_HUMAN,
            response="I completely understand your frustration, and I apologize. Let me get you connected with a team member right away. Can I have your name and phone number so they can call you back within 5 minutes?",
            follow_up_question="What's the best number to reach you?",
            priority=3
        )
    
    def _handle_off_topic(self, transcript: str, context: Dict) -> FallbackAction:
        business_name = context.get("business_name", "our company")
        industry = context.get("industry", "home services")
        
        if "robot" in transcript or "real" in transcript or "who are you" in transcript:
            return FallbackAction(
                fallback_type=FallbackType.REPHRASE,
                response=f"I'm Cortana, the AI assistant for {business_name}. I'm here to help you schedule service appointments and answer questions about our {industry} services. How can I help you today?",
                follow_up_question=None,
                priority=1
            )
        
        return FallbackAction(
            fallback_type=FallbackType.OFFER_ALTERNATIVES,
            response=f"I'm here to help you with {industry} services. Would you like to schedule an appointment, get information about our services, or something else?",
            follow_up_question="How can I help you with your home service needs?",
            priority=1
        )
    
    def _handle_pricing_blocker(self, context: Dict) -> FallbackAction:
        return FallbackAction(
            fallback_type=FallbackType.CALLBACK_OFFER,
            response="I understand you'd like specific pricing information. Our pricing depends on the specific job details, which our technician would assess on-site. I can schedule a free estimate visit, or have our team call you with more details. Which would you prefer?",
            follow_up_question="Would you like to schedule a free estimate?",
            priority=2
        )
    
    def _handle_knowledge_gap(self, context: Dict) -> FallbackAction:
        services = context.get("services", [])
        if services:
            services_str = ", ".join(services[:5])
            return FallbackAction(
                fallback_type=FallbackType.OFFER_ALTERNATIVES,
                response=f"Let me tell you about the services we offer: {services_str}. Is there something specific from this list you'd like help with?",
                follow_up_question="Which service can I help you with?",
                priority=1
            )
        
        return FallbackAction(
            fallback_type=FallbackType.CALLBACK_OFFER,
            response="That's a great question. Let me have one of our specialists call you back with detailed information. What's the best number to reach you?",
            follow_up_question=None,
            priority=2
        )
    
    def get_recovery_prompt(self, failed_action: str) -> str:
        """Get a recovery prompt after a failed action."""
        recovery_prompts = {
            "booking_failed": "I apologize, I wasn't able to complete that booking. Let me try again. What date works best for you?",
            "extraction_failed": "I didn't quite catch that. Could you please repeat your information?",
            "calendar_unavailable": "I'm having trouble checking our calendar right now. Would you prefer I have someone call you back to schedule?",
            "dispatch_failed": "I wasn't able to assign a technician just now, but I've logged your request. Someone will contact you shortly to confirm.",
            "sms_failed": "I couldn't send the confirmation text, but your appointment is confirmed. Would you like me to repeat the details?"
        }
        return recovery_prompts.get(failed_action, "Let me try that again for you.")
    
    def reset(self):
        """Reset confusion counter for new call."""
        self.confusion_count = 0


fallback_engine = FallbackEngine()
