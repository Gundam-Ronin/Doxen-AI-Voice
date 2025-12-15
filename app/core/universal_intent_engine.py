"""
Universal Intent Engine - Industry-agnostic intent detection for ANY home service business.
Detects intents like booking, pricing, emergency, reschedule, complaints, etc.
"""

from openai import OpenAI
import os
import json
from typing import Dict, List, Optional, Tuple
from enum import Enum


class UniversalIntent(str, Enum):
    BOOK_APPOINTMENT = "book_appointment"
    REQUEST_QUOTE = "request_quote"
    ASK_PRICING = "ask_pricing"
    ASK_AVAILABILITY = "ask_availability"
    ASK_SERVICES = "ask_services"
    ASK_COVERAGE = "ask_coverage"
    MEMBERSHIP_INQUIRY = "membership_inquiry"
    EMERGENCY = "emergency"
    WARRANTY_QUESTION = "warranty_question"
    RESCHEDULE = "reschedule"
    CANCEL = "cancel"
    TECHNICIAN_ETA = "technician_eta"
    SPEAK_TO_HUMAN = "speak_to_human"
    COMPLAINT = "complaint"
    WRONG_NUMBER = "wrong_number"
    PROVIDE_INFO = "provide_info"
    CONFIRMATION = "confirmation"
    DECLINE = "decline"
    FOLLOW_UP = "follow_up"
    GENERAL_QUESTION = "general_question"
    GREETING = "greeting"
    GOODBYE = "goodbye"
    UNKNOWN = "unknown"


INTENT_DESCRIPTIONS = {
    UniversalIntent.BOOK_APPOINTMENT: "Customer wants to schedule or book a service appointment",
    UniversalIntent.REQUEST_QUOTE: "Customer requesting an estimate or quote for services",
    UniversalIntent.ASK_PRICING: "Customer asking about prices, costs, or rates",
    UniversalIntent.ASK_AVAILABILITY: "Customer asking about available time slots or technician availability",
    UniversalIntent.ASK_SERVICES: "Customer asking what services are offered",
    UniversalIntent.ASK_COVERAGE: "Customer asking if their area/location is serviced",
    UniversalIntent.MEMBERSHIP_INQUIRY: "Customer asking about membership plans, subscriptions, or loyalty programs",
    UniversalIntent.EMERGENCY: "Urgent/emergency service needed (flooding, gas leak, no heat/AC, electrical hazard)",
    UniversalIntent.WARRANTY_QUESTION: "Customer asking about warranties, guarantees, or service agreements",
    UniversalIntent.RESCHEDULE: "Customer wants to change/reschedule existing appointment",
    UniversalIntent.CANCEL: "Customer wants to cancel an appointment or service",
    UniversalIntent.TECHNICIAN_ETA: "Customer asking when the technician will arrive",
    UniversalIntent.SPEAK_TO_HUMAN: "Customer explicitly requests to speak with a human/manager",
    UniversalIntent.COMPLAINT: "Customer expressing dissatisfaction, complaint, or concern",
    UniversalIntent.WRONG_NUMBER: "Caller has the wrong number or unrelated inquiry",
    UniversalIntent.PROVIDE_INFO: "Customer providing requested information (name, address, details)",
    UniversalIntent.CONFIRMATION: "Customer confirming something (yes, correct, that works)",
    UniversalIntent.DECLINE: "Customer declining an offer or suggestion",
    UniversalIntent.FOLLOW_UP: "Customer following up on previous service or inquiry",
    UniversalIntent.GENERAL_QUESTION: "General question about the business",
    UniversalIntent.GREETING: "Simple greeting (hello, hi)",
    UniversalIntent.GOODBYE: "Ending the conversation",
    UniversalIntent.UNKNOWN: "Cannot determine intent",
}


EMERGENCY_KEYWORDS = [
    "emergency", "urgent", "asap", "immediately", "right now", "flooding",
    "flood", "gas leak", "gas smell", "no heat", "no heating", "frozen pipes",
    "burst pipe", "electrical fire", "sparking", "no power", "power out",
    "smoke", "burning smell", "no hot water", "carbon monoxide", "sewage",
    "backup", "overflow", "dangerous", "hazard", "critical"
]


class UniversalIntentEngine:
    """Detects customer intent from speech in a business-agnostic way."""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
    def detect_intent(
        self,
        text: str,
        business_context: Optional[Dict] = None,
        conversation_history: Optional[List[Dict]] = None
    ) -> Tuple[UniversalIntent, float, Dict]:
        """
        Detect intent from customer speech.
        
        Args:
            text: The customer's speech text
            business_context: Optional business profile for context
            conversation_history: Optional list of previous messages
            
        Returns:
            Tuple of (intent, confidence, metadata)
        """
        if not text or not text.strip():
            return UniversalIntent.UNKNOWN, 0.0, {}
        
        text_lower = text.lower().strip()
        
        if self._is_emergency(text_lower):
            return UniversalIntent.EMERGENCY, 0.95, {"trigger": "keyword_match"}
        
        quick_intent = self._quick_intent_check(text_lower)
        if quick_intent:
            return quick_intent, 0.85, {"trigger": "pattern_match"}
        
        return self._ai_intent_detection(text, business_context, conversation_history)
    
    def _is_emergency(self, text: str) -> bool:
        """Check for emergency keywords."""
        return any(keyword in text for keyword in EMERGENCY_KEYWORDS)
    
    def _quick_intent_check(self, text: str) -> Optional[UniversalIntent]:
        """Quick pattern matching for common intents."""
        if any(word in text for word in ["hello", "hi ", "hey", "good morning", "good afternoon"]):
            if len(text.split()) <= 5:
                return UniversalIntent.GREETING
        
        if any(phrase in text for phrase in ["goodbye", "bye", "thank you", "thanks", "have a good"]):
            if len(text.split()) <= 8:
                return UniversalIntent.GOODBYE
        
        if any(phrase in text for phrase in ["yes", "yeah", "correct", "that's right", "sounds good", "perfect", "okay"]):
            if len(text.split()) <= 5:
                return UniversalIntent.CONFIRMATION
        
        if any(phrase in text for phrase in ["no ", "nope", "no thank", "not interested", "don't want"]):
            if len(text.split()) <= 6:
                return UniversalIntent.DECLINE
        
        booking_phrases = ["schedule", "book", "appointment", "set up", "come out", "send someone"]
        if any(phrase in text for phrase in booking_phrases):
            return UniversalIntent.BOOK_APPOINTMENT
        
        quote_phrases = ["quote", "estimate", "how much would", "cost to", "price for"]
        if any(phrase in text for phrase in quote_phrases):
            return UniversalIntent.REQUEST_QUOTE
        
        pricing_phrases = ["how much", "what's the price", "pricing", "rates", "cost", "charge"]
        if any(phrase in text for phrase in pricing_phrases):
            return UniversalIntent.ASK_PRICING
        
        if any(phrase in text for phrase in ["when can", "available", "availability", "open slot", "next opening"]):
            return UniversalIntent.ASK_AVAILABILITY
        
        if any(phrase in text for phrase in ["reschedule", "change the time", "different time", "move the appointment"]):
            return UniversalIntent.RESCHEDULE
        
        if any(phrase in text for phrase in ["cancel", "don't need", "nevermind", "changed my mind"]):
            return UniversalIntent.CANCEL
        
        if any(phrase in text for phrase in ["speak to someone", "talk to a person", "human", "manager", "supervisor"]):
            return UniversalIntent.SPEAK_TO_HUMAN
        
        if any(phrase in text for phrase in ["complaint", "unhappy", "disappointed", "frustrated", "problem with"]):
            return UniversalIntent.COMPLAINT
        
        if any(phrase in text for phrase in ["wrong number", "who is this", "what company"]):
            return UniversalIntent.WRONG_NUMBER
        
        if any(phrase in text for phrase in ["warranty", "guarantee", "covered", "service agreement"]):
            return UniversalIntent.WARRANTY_QUESTION
        
        if any(phrase in text for phrase in ["membership", "member", "subscribe", "plan", "discount program"]):
            return UniversalIntent.MEMBERSHIP_INQUIRY
        
        if any(phrase in text for phrase in ["do you service", "come to", "in my area", "zip code"]):
            return UniversalIntent.ASK_COVERAGE
        
        if any(phrase in text for phrase in ["what services", "do you do", "do you offer", "what can you"]):
            return UniversalIntent.ASK_SERVICES
        
        if any(phrase in text for phrase in ["where is", "when will", "eta", "on the way", "technician coming"]):
            return UniversalIntent.TECHNICIAN_ETA
        
        if any(phrase in text for phrase in ["following up", "called before", "checking on", "update on"]):
            return UniversalIntent.FOLLOW_UP
        
        return None
    
    def _ai_intent_detection(
        self,
        text: str,
        business_context: Optional[Dict] = None,
        conversation_history: Optional[List[Dict]] = None
    ) -> Tuple[UniversalIntent, float, Dict]:
        """Use AI to detect intent when pattern matching isn't sufficient."""
        try:
            intent_options = "\n".join([f"- {intent.value}: {desc}" for intent, desc in INTENT_DESCRIPTIONS.items()])
            
            context_str = ""
            if business_context:
                context_str = f"\nBusiness Type: {business_context.get('industry', 'general')}"
                context_str += f"\nServices: {', '.join(business_context.get('services', []))}"
            
            history_str = ""
            if conversation_history:
                recent = conversation_history[-5:]
                history_str = "\nRecent conversation:\n" + "\n".join([
                    f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
                    for msg in recent
                ])
            
            prompt = f"""Analyze this customer statement and determine their intent.

Customer said: "{text}"
{context_str}
{history_str}

Available intents:
{intent_options}

Respond with JSON only:
{{"intent": "intent_value", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=150,
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            intent_str = result.get("intent", "unknown")
            confidence = float(result.get("confidence", 0.5))
            
            try:
                intent = UniversalIntent(intent_str)
            except ValueError:
                intent = UniversalIntent.UNKNOWN
                confidence = 0.3
            
            return intent, confidence, {"reasoning": result.get("reasoning", ""), "trigger": "ai_detection"}
            
        except Exception as e:
            print(f"AI intent detection error: {e}")
            return UniversalIntent.UNKNOWN, 0.0, {"error": str(e)}
    
    def detect_multiple_intents(
        self,
        text: str,
        business_context: Optional[Dict] = None
    ) -> List[Tuple[UniversalIntent, float]]:
        """Detect multiple intents in a single statement."""
        try:
            intent_options = ", ".join([intent.value for intent in UniversalIntent])
            
            prompt = f"""Analyze this customer statement and identify ALL intents present.

Customer said: "{text}"

Available intents: {intent_options}

Respond with JSON array:
[{{"intent": "intent_value", "confidence": 0.0-1.0}}]"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=200,
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            intents_data = result.get("intents", result) if isinstance(result, dict) else result
            
            if not isinstance(intents_data, list):
                intents_data = [intents_data]
            
            intents = []
            for item in intents_data:
                try:
                    intent = UniversalIntent(item.get("intent", "unknown"))
                    confidence = float(item.get("confidence", 0.5))
                    intents.append((intent, confidence))
                except (ValueError, AttributeError):
                    continue
            
            return intents if intents else [(UniversalIntent.UNKNOWN, 0.0)]
            
        except Exception as e:
            print(f"Multiple intent detection error: {e}")
            return [(UniversalIntent.UNKNOWN, 0.0)]
    
    def get_intent_action(self, intent: UniversalIntent) -> Dict:
        """Get recommended action for an intent."""
        actions = {
            UniversalIntent.BOOK_APPOINTMENT: {
                "action": "initiate_booking",
                "collect_fields": ["name", "phone", "address", "service_type", "preferred_time"],
                "next_step": "check_availability"
            },
            UniversalIntent.REQUEST_QUOTE: {
                "action": "collect_quote_info",
                "collect_fields": ["name", "phone", "address", "service_description"],
                "next_step": "generate_quote"
            },
            UniversalIntent.ASK_PRICING: {
                "action": "provide_pricing",
                "collect_fields": ["service_type"],
                "next_step": "search_knowledgebase"
            },
            UniversalIntent.ASK_AVAILABILITY: {
                "action": "check_calendar",
                "collect_fields": ["service_type", "preferred_date"],
                "next_step": "offer_slots"
            },
            UniversalIntent.EMERGENCY: {
                "action": "emergency_dispatch",
                "collect_fields": ["name", "phone", "address", "emergency_description"],
                "next_step": "immediate_dispatch",
                "priority": "high"
            },
            UniversalIntent.RESCHEDULE: {
                "action": "lookup_appointment",
                "collect_fields": ["phone", "new_preferred_time"],
                "next_step": "modify_appointment"
            },
            UniversalIntent.CANCEL: {
                "action": "lookup_appointment",
                "collect_fields": ["phone"],
                "next_step": "cancel_appointment"
            },
            UniversalIntent.SPEAK_TO_HUMAN: {
                "action": "transfer_call",
                "collect_fields": [],
                "next_step": "human_handoff"
            },
            UniversalIntent.COMPLAINT: {
                "action": "log_complaint",
                "collect_fields": ["name", "phone", "complaint_details"],
                "next_step": "escalate"
            },
            UniversalIntent.TECHNICIAN_ETA: {
                "action": "lookup_dispatch",
                "collect_fields": ["phone"],
                "next_step": "provide_eta"
            },
            UniversalIntent.MEMBERSHIP_INQUIRY: {
                "action": "provide_info",
                "collect_fields": [],
                "next_step": "search_knowledgebase"
            },
            UniversalIntent.WARRANTY_QUESTION: {
                "action": "provide_info",
                "collect_fields": [],
                "next_step": "search_knowledgebase"
            },
            UniversalIntent.ASK_SERVICES: {
                "action": "provide_info",
                "collect_fields": [],
                "next_step": "search_knowledgebase"
            },
            UniversalIntent.ASK_COVERAGE: {
                "action": "check_coverage",
                "collect_fields": ["zip_code"],
                "next_step": "verify_coverage"
            },
            UniversalIntent.FOLLOW_UP: {
                "action": "lookup_history",
                "collect_fields": ["phone"],
                "next_step": "provide_update"
            },
        }
        
        return actions.get(intent, {
            "action": "continue_conversation",
            "collect_fields": [],
            "next_step": "respond_naturally"
        })


universal_intent_engine = UniversalIntentEngine()
