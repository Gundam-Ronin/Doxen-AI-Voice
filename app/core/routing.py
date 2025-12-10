from datetime import datetime, time
from typing import Dict, Any, Optional

class RoutingManager:
    def __init__(self):
        self.default_hours = {
            "monday": {"open": "09:00", "close": "17:00"},
            "tuesday": {"open": "09:00", "close": "17:00"},
            "wednesday": {"open": "09:00", "close": "17:00"},
            "thursday": {"open": "09:00", "close": "17:00"},
            "friday": {"open": "09:00", "close": "17:00"},
            "saturday": {"open": "10:00", "close": "14:00"},
            "sunday": None
        }
    
    def is_business_hours(self, business_hours: Dict = None) -> bool:
        hours = business_hours or self.default_hours
        now = datetime.now()
        day_name = now.strftime("%A").lower()
        
        day_hours = hours.get(day_name)
        if not day_hours:
            return False
        
        try:
            open_time = datetime.strptime(day_hours["open"], "%H:%M").time()
            close_time = datetime.strptime(day_hours["close"], "%H:%M").time()
            current_time = now.time()
            
            return open_time <= current_time <= close_time
        except (KeyError, ValueError):
            return True
    
    def get_routing_decision(
        self,
        business_hours: Dict = None,
        is_emergency: bool = False,
        has_available_tech: bool = True
    ) -> Dict[str, Any]:
        in_hours = self.is_business_hours(business_hours)
        
        if is_emergency:
            return {
                "route": "emergency",
                "action": "dispatch_immediately",
                "message": "This is being treated as an emergency. A technician will be notified immediately.",
                "priority": "high"
            }
        
        if in_hours:
            if has_available_tech:
                return {
                    "route": "normal",
                    "action": "ai_handle",
                    "message": None,
                    "priority": "normal"
                }
            else:
                return {
                    "route": "overflow",
                    "action": "schedule_callback",
                    "message": "All technicians are currently busy. Would you like us to call you back?",
                    "priority": "normal"
                }
        else:
            return {
                "route": "after_hours",
                "action": "voicemail",
                "message": "Thank you for calling. We're currently closed. Please leave a message and we'll return your call during business hours.",
                "priority": "low"
            }
    
    def get_next_available_time(self, business_hours: Dict = None) -> Optional[datetime]:
        hours = business_hours or self.default_hours
        now = datetime.now()
        
        for days_ahead in range(7):
            check_date = now + timedelta(days=days_ahead)
            day_name = check_date.strftime("%A").lower()
            day_hours = hours.get(day_name)
            
            if day_hours:
                open_time = datetime.strptime(day_hours["open"], "%H:%M").time()
                potential_time = check_date.replace(
                    hour=open_time.hour,
                    minute=open_time.minute,
                    second=0,
                    microsecond=0
                )
                
                if potential_time > now:
                    return potential_time
        
        return None

from datetime import timedelta

routing_manager = RoutingManager()
