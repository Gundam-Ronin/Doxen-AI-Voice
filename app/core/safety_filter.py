"""
Phase 7.1 - Real-time Safety Filters
Protects against inappropriate content and ensures safe AI responses.
"""

import re
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class SafetyCategory(Enum):
    SAFE = "safe"
    CAUTION = "caution"
    BLOCK = "block"
    EMERGENCY = "emergency"


@dataclass
class SafetyResult:
    category: SafetyCategory
    is_safe: bool
    flags: List[str]
    sanitized_text: Optional[str]
    action_required: Optional[str]


class SafetyFilter:
    """Real-time content safety filter for voice AI."""
    
    def __init__(self):
        self.blocked_patterns = [
            r'\b(password|credit\s*card|ssn|social\s*security)\b',
            r'\b(bank\s*account|routing\s*number|pin\s*number)\b',
            r'\b(hack|exploit|illegal|drug|weapon)\b',
        ]
        
        self.pii_patterns = {
            "ssn": r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b',
            "credit_card": r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            "bank_account": r'\b\d{8,17}\b',
        }
        
        self.emergency_patterns = [
            r'\b(gas\s*leak|smell\s*gas|carbon\s*monoxide)\b',
            r'\b(fire|smoke|burning)\b',
            r'\b(flooding|water\s*everywhere|burst\s*pipe)\b',
            r'\b(no\s*heat|freezing|pipes\s*frozen)\b',
            r'\b(electrical\s*fire|sparking|shock)\b',
            r'\b(can\'t\s*breathe|medical|emergency|911)\b',
        ]
        
        self.inappropriate_patterns = [
            r'\b(profanity_placeholder)\b',
        ]
        
        self.safe_responses = {
            "pii_request": "I'm not able to collect sensitive financial information over the phone. Our office can help you with that securely.",
            "blocked_topic": "I'm only able to help with scheduling and service questions. Is there something else I can help you with?",
            "emergency_detected": "This sounds like an emergency. For immediate safety concerns, please call 911. For urgent service, I can dispatch a technician right away.",
        }
    
    def filter_input(self, text: str) -> SafetyResult:
        """Filter incoming customer speech for safety concerns."""
        flags = []
        text_lower = text.lower()
        
        for pattern in self.emergency_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                flags.append("emergency_detected")
                return SafetyResult(
                    category=SafetyCategory.EMERGENCY,
                    is_safe=True,
                    flags=flags,
                    sanitized_text=text,
                    action_required="dispatch_emergency"
                )
        
        for pii_type, pattern in self.pii_patterns.items():
            if re.search(pattern, text):
                flags.append(f"pii_detected:{pii_type}")
        
        if flags:
            sanitized = self._sanitize_pii(text)
            return SafetyResult(
                category=SafetyCategory.CAUTION,
                is_safe=True,
                flags=flags,
                sanitized_text=sanitized,
                action_required="log_pii_attempt"
            )
        
        for pattern in self.blocked_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                flags.append("blocked_topic_requested")
                return SafetyResult(
                    category=SafetyCategory.BLOCK,
                    is_safe=False,
                    flags=flags,
                    sanitized_text=None,
                    action_required="redirect_topic"
                )
        
        return SafetyResult(
            category=SafetyCategory.SAFE,
            is_safe=True,
            flags=[],
            sanitized_text=text,
            action_required=None
        )
    
    def filter_output(self, response: str, context: Dict[str, Any] = None) -> SafetyResult:
        """Filter AI response before sending to customer."""
        flags = []
        
        price_pattern = r'\$\d+(?:,\d{3})*(?:\.\d{2})?'
        if re.search(price_pattern, response):
            if not context or not context.get("pricing_approved"):
                flags.append("unapproved_pricing")
        
        commitment_patterns = [
            r'\b(we\s+guarantee|guaranteed|promise)\b',
            r'\b(definitely|absolutely\s+will|for\s+sure)\b',
            r'\b(no\s+charge|free\s+of\s+charge|on\s+the\s+house)\b',
        ]
        
        for pattern in commitment_patterns:
            if re.search(pattern, response, re.IGNORECASE):
                flags.append("commitment_language")
        
        if flags:
            return SafetyResult(
                category=SafetyCategory.CAUTION,
                is_safe=True,
                flags=flags,
                sanitized_text=response,
                action_required="review_response"
            )
        
        return SafetyResult(
            category=SafetyCategory.SAFE,
            is_safe=True,
            flags=[],
            sanitized_text=response,
            action_required=None
        )
    
    def _sanitize_pii(self, text: str) -> str:
        """Remove PII from text for logging."""
        sanitized = text
        
        for pii_type, pattern in self.pii_patterns.items():
            sanitized = re.sub(pattern, f"[REDACTED_{pii_type.upper()}]", sanitized)
        
        return sanitized
    
    def get_safe_response(self, situation: str) -> str:
        """Get a pre-approved safe response for a situation."""
        return self.safe_responses.get(situation, "How can I help you with your service needs today?")
    
    def validate_booking_details(self, booking: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate booking details for safety and completeness."""
        issues = []
        
        required = ["customer_name", "phone", "address", "service_type"]
        for field in required:
            if not booking.get(field):
                issues.append(f"missing_{field}")
        
        if booking.get("appointment_time"):
            from datetime import datetime, timedelta
            try:
                apt_time = booking["appointment_time"]
                if isinstance(apt_time, str):
                    apt_time = datetime.fromisoformat(apt_time)
                
                now = datetime.now()
                if apt_time < now:
                    issues.append("appointment_in_past")
                elif apt_time > now + timedelta(days=90):
                    issues.append("appointment_too_far_future")
                    
            except Exception:
                issues.append("invalid_appointment_time")
        
        is_valid = len(issues) == 0
        return is_valid, issues


safety_filter = SafetyFilter()
