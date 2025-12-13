import re
from typing import Dict, List, Tuple
from enum import Enum


class CustomerIntent(Enum):
    BOOK_APPOINTMENT = "book_appointment"
    CHECK_AVAILABILITY = "check_availability"
    CANCEL_APPOINTMENT = "cancel_appointment"
    RESCHEDULE = "reschedule"
    EMERGENCY = "emergency"
    PRICING_INQUIRY = "pricing_inquiry"
    SERVICE_INFO = "service_info"
    SPEAK_TO_HUMAN = "speak_to_human"
    COMPLAINT = "complaint"
    CONFIRMATION = "confirmation"
    DECLINE = "decline"
    PROVIDE_INFO = "provide_info"
    GREETING = "greeting"
    GOODBYE = "goodbye"
    UNKNOWN = "unknown"


INTENT_PATTERNS = {
    CustomerIntent.BOOK_APPOINTMENT: [
        r'\b(book|schedule|make|set up|arrange)\b.*(appointment|visit|service|time)',
        r'\b(need|want|like)\b.*(someone|technician|plumber|electrician).*(come|visit)',
        r'\bcan you (come|send someone|schedule)',
        r'\bi\'?d like to (book|schedule|make)',
        r'\bwhen can (you|someone) come',
    ],
    CustomerIntent.CHECK_AVAILABILITY: [
        r'\b(what|when).*(available|availability|open|free)',
        r'\bdo you have.*(openings|slots|time)',
        r'\bwhat times do you have',
        r'\bare you (open|available)',
    ],
    CustomerIntent.CANCEL_APPOINTMENT: [
        r'\b(cancel|canceling)\b.*appointment',
        r'\bneed to cancel',
        r'\bcan\'t make it',
    ],
    CustomerIntent.RESCHEDULE: [
        r'\b(reschedule|change|move)\b.*appointment',
        r'\bneed to (change|move) my',
        r'\bcan we (change|move) the time',
    ],
    CustomerIntent.EMERGENCY: [
        r'\b(emergency|urgent|immediately|right now|asap)\b',
        r'\b(flooding|flood|leak|burst|broken|no heat|no hot water)\b',
        r'\bwater everywhere',
        r'\bgas (leak|smell)',
        r'\belectrical (fire|sparks|emergency)',
    ],
    CustomerIntent.PRICING_INQUIRY: [
        r'\bhow much (do|does|will|would)',
        r'\bwhat (do|does|will|would).*(cost|charge|price)',
        r'\bpricing|prices|rates|fees',
        r'\bget a (quote|estimate)',
    ],
    CustomerIntent.SERVICE_INFO: [
        r'\bdo you (do|offer|provide|handle)',
        r'\bwhat services',
        r'\bcan you (help with|fix|repair|install)',
        r'\btell me (about|more)',
    ],
    CustomerIntent.SPEAK_TO_HUMAN: [
        r'\b(speak|talk).*(human|person|someone|representative|agent)',
        r'\breal person',
        r'\btransfer me',
        r'\boperator',
    ],
    CustomerIntent.COMPLAINT: [
        r'\b(complain|complaint|unhappy|dissatisfied|problem with)',
        r'\bterrible service',
        r'\bwant (a refund|my money back)',
        r'\bspeak to (manager|supervisor)',
    ],
    CustomerIntent.CONFIRMATION: [
        r'^(yes|yeah|yep|sure|okay|ok|correct|right|absolutely|definitely|please)$',
        r'\bthat (works|sounds good|\'s good|\'s fine)',
        r'\bperfect|great|excellent',
        r'\blet\'s do (it|that)',
    ],
    CustomerIntent.DECLINE: [
        r'^(no|nope|nah|not really|no thanks)$',
        r'\bthat (doesn\'t work|won\'t work)',
        r'\bi\'ll pass',
        r'\bmaybe later',
    ],
    CustomerIntent.PROVIDE_INFO: [
        r'\bmy (name|phone|number|address|email) is',
        r'\bi\'m at|i live at',
        r'\byou can reach me at',
        r'\bthe address is',
    ],
    CustomerIntent.GREETING: [
        r'^(hi|hello|hey|good morning|good afternoon|good evening)$',
        r'\bhow are you',
    ],
    CustomerIntent.GOODBYE: [
        r'\b(bye|goodbye|see you|take care|thanks|thank you)\b.*$',
        r'\bthat\'s all|that\'s it',
        r'\bhave a (good|nice|great) (day|one)',
    ],
}


def detect_intent(text: str) -> Tuple[CustomerIntent, float]:
    """Detect the primary intent from user speech."""
    text_lower = text.lower().strip()
    
    scores = {}
    
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                scores[intent] = scores.get(intent, 0) + 1
    
    if not scores:
        return CustomerIntent.UNKNOWN, 0.0
    
    best_intent = max(scores, key=scores.get)
    confidence = min(scores[best_intent] / 2.0, 1.0)
    
    return best_intent, confidence


def detect_all_intents(text: str) -> List[Tuple[CustomerIntent, float]]:
    """Detect all matching intents with confidence scores."""
    text_lower = text.lower().strip()
    
    scores = {}
    
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                scores[intent] = scores.get(intent, 0) + 1
    
    results = [(intent, min(score / 2.0, 1.0)) for intent, score in scores.items()]
    return sorted(results, key=lambda x: x[1], reverse=True)


def get_intent_response_hint(intent: CustomerIntent) -> Dict:
    """Get hints for how to respond to a given intent."""
    hints = {
        CustomerIntent.BOOK_APPOINTMENT: {
            "action": "offer_slots",
            "collect": ["name", "phone", "address", "preferred_time"],
            "response_type": "appointment_flow"
        },
        CustomerIntent.CHECK_AVAILABILITY: {
            "action": "list_availability",
            "collect": [],
            "response_type": "availability_info"
        },
        CustomerIntent.EMERGENCY: {
            "action": "emergency_dispatch",
            "collect": ["name", "phone", "address", "issue"],
            "response_type": "emergency_flow",
            "priority": "high"
        },
        CustomerIntent.PRICING_INQUIRY: {
            "action": "provide_pricing",
            "collect": ["service_type"],
            "response_type": "pricing_info"
        },
        CustomerIntent.SPEAK_TO_HUMAN: {
            "action": "transfer_or_callback",
            "collect": ["phone"],
            "response_type": "transfer_flow"
        },
        CustomerIntent.CONFIRMATION: {
            "action": "confirm_and_proceed",
            "collect": [],
            "response_type": "confirmation"
        },
        CustomerIntent.DECLINE: {
            "action": "offer_alternatives",
            "collect": [],
            "response_type": "alternative_offer"
        },
        CustomerIntent.GOODBYE: {
            "action": "end_call",
            "collect": [],
            "response_type": "farewell"
        },
    }
    return hints.get(intent, {"action": "continue_conversation", "collect": [], "response_type": "general"})


def is_booking_intent(intent: CustomerIntent) -> bool:
    """Check if intent is related to booking."""
    return intent in [
        CustomerIntent.BOOK_APPOINTMENT,
        CustomerIntent.CHECK_AVAILABILITY,
        CustomerIntent.RESCHEDULE
    ]


def is_urgent(intent: CustomerIntent) -> bool:
    """Check if intent requires urgent handling."""
    return intent == CustomerIntent.EMERGENCY
