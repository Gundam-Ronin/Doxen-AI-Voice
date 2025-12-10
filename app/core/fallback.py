import os
from typing import Dict, Any
from datetime import datetime, timedelta

class FallbackManager:
    def __init__(self):
        self.error_counts = {}
        self.last_errors = {}
        self.threshold = 5
        self.window_minutes = 5
    
    def record_error(self, service: str, error: str):
        now = datetime.utcnow()
        
        if service not in self.error_counts:
            self.error_counts[service] = []
        
        self.error_counts[service].append(now)
        self.last_errors[service] = {"error": error, "timestamp": now}
        
        cutoff = now - timedelta(minutes=self.window_minutes)
        self.error_counts[service] = [
            t for t in self.error_counts[service] if t > cutoff
        ]
    
    def is_service_healthy(self, service: str) -> bool:
        if service not in self.error_counts:
            return True
        
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=self.window_minutes)
        recent_errors = [t for t in self.error_counts[service] if t > cutoff]
        
        return len(recent_errors) < self.threshold
    
    def get_fallback_response(self, service: str) -> Dict[str, Any]:
        fallback_responses = {
            "openai": {
                "message": "I apologize, but I'm having some technical difficulties. Would you like me to have someone call you back shortly?",
                "action": "offer_callback",
                "tts_text": "I apologize, but I'm having some technical difficulties. Would you like me to have someone call you back shortly?"
            },
            "calendar": {
                "message": "I'm unable to check our calendar at the moment. Can I take your information and have someone call you to schedule?",
                "action": "collect_info",
                "tts_text": "I'm unable to check our calendar at the moment. Can I take your information and have someone call you to schedule?"
            },
            "dispatch": {
                "message": "I'm having trouble reaching our dispatch system. Your request has been noted and a technician will contact you shortly.",
                "action": "log_for_manual",
                "tts_text": "I'm having trouble reaching our dispatch system. Your request has been noted and a technician will contact you shortly."
            },
            "database": {
                "message": "We're experiencing some technical issues. Please try again in a few moments or call back later.",
                "action": "retry_later",
                "tts_text": "We're experiencing some technical issues. Please try again in a few moments or call back later."
            }
        }
        
        return fallback_responses.get(service, {
            "message": "We're experiencing technical difficulties. Please hold or call back shortly.",
            "action": "hold",
            "tts_text": "We're experiencing technical difficulties. Please hold or call back shortly."
        })
    
    def get_health_status(self) -> Dict[str, Any]:
        services = ["openai", "calendar", "dispatch", "database", "twilio"]
        status = {}
        
        for service in services:
            is_healthy = self.is_service_healthy(service)
            last_error = self.last_errors.get(service)
            
            status[service] = {
                "healthy": is_healthy,
                "last_error": last_error.get("error") if last_error else None,
                "last_error_time": last_error.get("timestamp").isoformat() if last_error else None
            }
        
        overall_healthy = all(s["healthy"] for s in status.values())
        
        return {
            "overall": "healthy" if overall_healthy else "degraded",
            "services": status,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def clear_errors(self, service: str = None):
        if service:
            self.error_counts.pop(service, None)
            self.last_errors.pop(service, None)
        else:
            self.error_counts = {}
            self.last_errors = {}

fallback_manager = FallbackManager()
