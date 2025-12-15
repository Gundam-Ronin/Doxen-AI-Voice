"""
Universal Dispatch Engine - Configurable dispatch modes for any home service business.
Supports: round-robin, skill-based, location-based, availability, manual, emergency modes.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import math
import os
from twilio.rest import Client as TwilioClient


class DispatchMode(str, Enum):
    ROUND_ROBIN = "round_robin"
    SKILL_BASED = "skill_based"
    LOCATION_BASED = "location_based"
    AVAILABILITY_BASED = "availability"
    MANUAL = "manual"
    EMERGENCY = "emergency"
    PREFERRED_FIRST = "preferred_first"


@dataclass
class TechnicianScore:
    """Score a technician for a job."""
    technician_id: int
    name: str
    phone: str
    total_score: float
    skill_match: float
    distance_score: float
    availability_score: float
    workload_score: float
    reasons: List[str]


class UniversalDispatchEngine:
    """Industry-agnostic technician dispatch engine."""
    
    def __init__(self):
        self.twilio_client = None
        self._init_twilio()
    
    def _init_twilio(self):
        """Initialize Twilio client if credentials are available."""
        try:
            account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
            auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
            if account_sid and auth_token:
                self.twilio_client = TwilioClient(account_sid, auth_token)
        except Exception as e:
            print(f"Twilio initialization error: {e}")
    
    def match_technician(
        self,
        technicians: List[Dict],
        job_requirements: Dict,
        dispatch_rules: Dict,
        customer_location: Optional[Dict] = None
    ) -> Optional[TechnicianScore]:
        """
        Match the best technician for a job based on dispatch rules.
        
        Args:
            technicians: List of available technicians
            job_requirements: Job details including service type, skills needed, urgency
            dispatch_rules: Business dispatch configuration
            customer_location: Customer's location (zip, coordinates)
            
        Returns:
            Best matching technician or None
        """
        if not technicians:
            return None
        
        mode = DispatchMode(dispatch_rules.get("mode", "skill_based"))
        
        if mode == DispatchMode.MANUAL:
            return None
        
        scored_technicians = []
        for tech in technicians:
            if not self._is_available(tech, job_requirements):
                continue
            
            score = self._score_technician(tech, job_requirements, dispatch_rules, customer_location, mode)
            if score.total_score > 0:
                scored_technicians.append(score)
        
        if not scored_technicians:
            return None
        
        scored_technicians.sort(key=lambda x: x.total_score, reverse=True)
        
        return scored_technicians[0]
    
    def match_multiple_technicians(
        self,
        technicians: List[Dict],
        job_requirements: Dict,
        dispatch_rules: Dict,
        customer_location: Optional[Dict] = None,
        count: int = 3
    ) -> List[TechnicianScore]:
        """Get top N matching technicians for a job."""
        if not technicians:
            return []
        
        mode = DispatchMode(dispatch_rules.get("mode", "skill_based"))
        
        scored_technicians = []
        for tech in technicians:
            if not self._is_available(tech, job_requirements):
                continue
            
            score = self._score_technician(tech, job_requirements, dispatch_rules, customer_location, mode)
            if score.total_score > 0:
                scored_technicians.append(score)
        
        scored_technicians.sort(key=lambda x: x.total_score, reverse=True)
        
        return scored_technicians[:count]
    
    def _is_available(self, technician: Dict, job_requirements: Dict) -> bool:
        """Check if technician is available for the job."""
        if technician.get("status") not in ["active", None]:
            return False
        
        if not technician.get("is_available", True):
            return False
        
        preferred_time = job_requirements.get("preferred_time")
        if preferred_time and technician.get("availability"):
            pass
        
        return True
    
    def _score_technician(
        self,
        technician: Dict,
        job_requirements: Dict,
        dispatch_rules: Dict,
        customer_location: Optional[Dict],
        mode: DispatchMode
    ) -> TechnicianScore:
        """Calculate a composite score for a technician."""
        reasons = []
        
        skill_score = self._calculate_skill_match(
            technician.get("skills", []),
            job_requirements.get("required_skills", []),
            job_requirements.get("service_type")
        )
        if skill_score > 0.8:
            reasons.append("Strong skill match")
        
        distance_score = 1.0
        if customer_location and customer_location.get("zip_code"):
            distance_score = self._calculate_distance_score(
                technician.get("home_zip"),
                customer_location.get("zip_code"),
                technician.get("service_radius_miles", 25),
                dispatch_rules.get("max_distance_miles", 50)
            )
            if distance_score > 0.7:
                reasons.append("Close proximity")
        
        availability_score = 1.0
        if job_requirements.get("urgency") == "emergency":
            availability_score = 1.0 if technician.get("is_available") else 0.0
            if availability_score > 0:
                reasons.append("Available now")
        
        workload_score = self._calculate_workload_score(technician)
        if workload_score > 0.7:
            reasons.append("Light workload")
        
        if mode == DispatchMode.SKILL_BASED:
            weights = {"skill": 0.5, "distance": 0.2, "availability": 0.2, "workload": 0.1}
        elif mode == DispatchMode.LOCATION_BASED:
            weights = {"skill": 0.2, "distance": 0.5, "availability": 0.2, "workload": 0.1}
        elif mode == DispatchMode.EMERGENCY:
            weights = {"skill": 0.1, "distance": 0.3, "availability": 0.5, "workload": 0.1}
        elif mode == DispatchMode.AVAILABILITY_BASED:
            weights = {"skill": 0.2, "distance": 0.2, "availability": 0.4, "workload": 0.2}
        elif mode == DispatchMode.ROUND_ROBIN:
            weights = {"skill": 0.1, "distance": 0.1, "availability": 0.1, "workload": 0.7}
        else:
            weights = {"skill": 0.4, "distance": 0.2, "availability": 0.2, "workload": 0.2}
        
        total_score = (
            skill_score * weights["skill"] +
            distance_score * weights["distance"] +
            availability_score * weights["availability"] +
            workload_score * weights["workload"]
        )
        
        return TechnicianScore(
            technician_id=technician.get("id"),
            name=technician.get("name", "Unknown"),
            phone=technician.get("phone", ""),
            total_score=total_score,
            skill_match=skill_score,
            distance_score=distance_score,
            availability_score=availability_score,
            workload_score=workload_score,
            reasons=reasons
        )
    
    def _calculate_skill_match(
        self,
        tech_skills: List[str],
        required_skills: List[str],
        service_type: Optional[str] = None
    ) -> float:
        """Calculate skill match score (0-1)."""
        if not required_skills and not service_type:
            return 0.7
        
        tech_skills_lower = [s.lower() for s in tech_skills]
        
        if service_type:
            service_lower = service_type.lower()
            for skill in tech_skills_lower:
                if service_lower in skill or skill in service_lower:
                    return 1.0
        
        if not required_skills:
            return 0.5
        
        required_lower = [s.lower() for s in required_skills]
        matches = sum(1 for r in required_lower if any(r in t or t in r for t in tech_skills_lower))
        
        return matches / len(required_lower) if required_lower else 0.5
    
    def _calculate_distance_score(
        self,
        tech_zip: Optional[str],
        customer_zip: Optional[str],
        tech_radius: int,
        max_distance: int
    ) -> float:
        """Calculate distance-based score (0-1)."""
        if not tech_zip or not customer_zip:
            return 0.5
        
        if tech_zip[:3] == customer_zip[:3]:
            return 1.0
        elif tech_zip[:2] == customer_zip[:2]:
            return 0.7
        elif tech_zip[:1] == customer_zip[:1]:
            return 0.4
        else:
            return 0.2
    
    def _calculate_workload_score(self, technician: Dict) -> float:
        """Calculate workload score (higher = less busy)."""
        current_jobs = technician.get("current_job_count", 0)
        
        if current_jobs == 0:
            return 1.0
        elif current_jobs <= 2:
            return 0.7
        elif current_jobs <= 4:
            return 0.4
        else:
            return 0.1
    
    def dispatch_technician(
        self,
        technician: Dict,
        appointment: Dict,
        customer: Dict,
        business: Dict,
        dispatch_mode: str = "skill_based"
    ) -> Dict:
        """
        Dispatch a technician to an appointment via SMS.
        
        Returns:
            Dispatch result with status and message ID
        """
        try:
            tech_name = technician.get("name", "Technician")
            tech_phone = technician.get("phone")
            
            customer_name = customer.get("name", "Customer")
            customer_address = customer.get("address", "Address TBD")
            customer_phone = customer.get("phone_number", "")
            
            service_type = appointment.get("service_type", "Service Call")
            urgency = appointment.get("urgency_level", "normal")
            start_time = appointment.get("start_time")
            notes = appointment.get("customer_notes", "")
            
            if isinstance(start_time, datetime):
                time_str = start_time.strftime("%B %d at %I:%M %p")
            else:
                time_str = str(start_time) if start_time else "ASAP"
            
            urgency_prefix = "🚨 EMERGENCY: " if urgency == "emergency" else ""
            
            message = f"""{urgency_prefix}New Job Assignment

Service: {service_type}
Customer: {customer_name}
Address: {customer_address}
Phone: {customer_phone}
Time: {time_str}
{f'Notes: {notes}' if notes else ''}

Reply YES to confirm or call dispatch for questions."""

            result = {
                "technician_id": technician.get("id"),
                "technician_name": tech_name,
                "status": "pending",
                "dispatch_mode": dispatch_mode,
                "message": message
            }
            
            if self.twilio_client and tech_phone:
                from_number = os.environ.get("TWILIO_PHONE_NUMBER")
                if from_number:
                    sms = self.twilio_client.messages.create(
                        body=message,
                        from_=from_number,
                        to=tech_phone
                    )
                    result["status"] = "sent"
                    result["message_sid"] = sms.sid
                else:
                    result["status"] = "failed"
                    result["error"] = "No Twilio phone number configured"
            else:
                result["status"] = "skipped"
                result["error"] = "Twilio not configured or no phone number"
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def send_dispatch_update(
        self,
        technician: Dict,
        update_type: str,
        details: Dict
    ) -> Dict:
        """Send status update SMS to technician."""
        try:
            messages = {
                "cancelled": f"Job cancelled: {details.get('reason', 'Customer request')}",
                "rescheduled": f"Job rescheduled to {details.get('new_time', 'TBD')}",
                "updated": f"Job update: {details.get('message', 'Please check app for details')}",
                "reminder": f"Reminder: Job at {details.get('address', 'TBD')} in {details.get('minutes', 30)} minutes"
            }
            
            message = messages.get(update_type, details.get("message", "Update from dispatch"))
            
            if self.twilio_client and technician.get("phone"):
                from_number = os.environ.get("TWILIO_PHONE_NUMBER")
                if from_number:
                    sms = self.twilio_client.messages.create(
                        body=message,
                        from_=from_number,
                        to=technician.get("phone")
                    )
                    return {"status": "sent", "message_sid": sms.sid}
            
            return {"status": "skipped", "message": message}
            
        except Exception as e:
            return {"status": "error", "error": str(e)}


universal_dispatch_engine = UniversalDispatchEngine()
