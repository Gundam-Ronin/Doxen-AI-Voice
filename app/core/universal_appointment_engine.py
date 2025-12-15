"""
Universal Appointment Engine - Adaptive scheduling for ANY home service business.
Works with any service type, duration, and resource requirements.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta, time
from dataclasses import dataclass
import os
import json


@dataclass
class TimeSlot:
    """Represents an available time slot."""
    start: datetime
    end: datetime
    duration_minutes: int
    technician_id: Optional[int] = None
    technician_name: Optional[str] = None


@dataclass
class BookingResult:
    """Result of a booking attempt."""
    success: bool
    appointment_id: Optional[str] = None
    google_event_id: Optional[str] = None
    message: str = ""
    slot: Optional[TimeSlot] = None
    error: Optional[str] = None


class UniversalAppointmentEngine:
    """Industry-agnostic appointment scheduling engine."""
    
    def __init__(self):
        self.calendar_service = None
        self._init_calendar()
    
    def _init_calendar(self):
        """Initialize Google Calendar service if available."""
        try:
            from app.core.calendar import CalendarService
            self.calendar_service = CalendarService()
        except Exception as e:
            print(f"Calendar initialization note: {e}")
    
    def get_available_slots(
        self,
        business: Dict,
        service_category: Optional[Dict] = None,
        preferred_date: Optional[datetime] = None,
        days_to_check: int = 7,
        technician_id: Optional[int] = None
    ) -> List[TimeSlot]:
        """
        Get available appointment slots based on business hours and calendar.
        
        Args:
            business: Business profile with hours and calendar settings
            service_category: Optional service category with duration
            preferred_date: Start date for slot search
            days_to_check: How many days to search
            technician_id: Optional specific technician
            
        Returns:
            List of available time slots
        """
        if preferred_date is None:
            preferred_date = datetime.now()
        
        duration = 60
        if service_category:
            duration = service_category.get("default_duration_minutes", 60)
        
        business_hours = business.get("business_hours") or business.get("hours", {})
        if not business_hours:
            business_hours = {
                "monday": ["09:00-17:00"],
                "tuesday": ["09:00-17:00"],
                "wednesday": ["09:00-17:00"],
                "thursday": ["09:00-17:00"],
                "friday": ["09:00-17:00"]
            }
        
        calendar_id = None
        if business.get("calendar_integration"):
            calendar_id = business["calendar_integration"].get("google_calendar_id")
        
        busy_times = []
        if self.calendar_service and calendar_id:
            busy_times = self._get_busy_times(calendar_id, preferred_date, days_to_check)
        
        slots = []
        current_date = preferred_date.date()
        
        for day_offset in range(days_to_check):
            check_date = current_date + timedelta(days=day_offset)
            day_name = check_date.strftime("%A").lower()
            
            day_hours = business_hours.get(day_name, [])
            if not day_hours:
                continue
            
            for time_range in day_hours:
                day_slots = self._generate_slots_for_range(
                    check_date, time_range, duration, busy_times
                )
                slots.extend(day_slots)
        
        return slots[:20]
    
    def _generate_slots_for_range(
        self,
        date: datetime,
        time_range: str,
        duration_minutes: int,
        busy_times: List[Tuple[datetime, datetime]]
    ) -> List[TimeSlot]:
        """Generate available slots for a time range."""
        slots = []
        
        try:
            start_str, end_str = time_range.split("-")
            start_hour, start_min = map(int, start_str.split(":"))
            end_hour, end_min = map(int, end_str.split(":"))
            
            slot_start = datetime.combine(date, time(start_hour, start_min))
            range_end = datetime.combine(date, time(end_hour, end_min))
            
            now = datetime.now()
            if slot_start < now:
                slot_start = now + timedelta(minutes=30 - now.minute % 30)
            
            while slot_start + timedelta(minutes=duration_minutes) <= range_end:
                slot_end = slot_start + timedelta(minutes=duration_minutes)
                
                is_busy = any(
                    (busy_start <= slot_start < busy_end) or
                    (busy_start < slot_end <= busy_end) or
                    (slot_start <= busy_start and slot_end >= busy_end)
                    for busy_start, busy_end in busy_times
                )
                
                if not is_busy:
                    slots.append(TimeSlot(
                        start=slot_start,
                        end=slot_end,
                        duration_minutes=duration_minutes
                    ))
                
                slot_start += timedelta(minutes=30)
                
        except Exception as e:
            print(f"Error generating slots: {e}")
        
        return slots
    
    def _get_busy_times(
        self,
        calendar_id: str,
        start_date: datetime,
        days: int
    ) -> List[Tuple[datetime, datetime]]:
        """Get busy times from Google Calendar."""
        busy_times = []
        
        try:
            if not self.calendar_service:
                return busy_times
            
            service = getattr(self.calendar_service, 'service', None)
            if not service:
                return busy_times
            
            time_min = start_date.isoformat() + "Z"
            time_max = (start_date + timedelta(days=days)).isoformat() + "Z"
            
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            
            events = events_result.get("items", [])
            
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                end = event["end"].get("dateTime", event["end"].get("date"))
                
                start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                
                if start_dt.tzinfo:
                    start_dt = start_dt.replace(tzinfo=None)
                if end_dt.tzinfo:
                    end_dt = end_dt.replace(tzinfo=None)
                
                busy_times.append((start_dt, end_dt))
                
        except Exception as e:
            print(f"Error fetching busy times: {e}")
        
        return busy_times
    
    def format_slots_for_voice(self, slots: List[TimeSlot], count: int = 3) -> str:
        """Format time slots for voice response."""
        if not slots:
            return "I don't have any available slots in the next week."
        
        display_slots = slots[:count]
        
        slot_strings = []
        for slot in display_slots:
            day = slot.start.strftime("%A")
            date = slot.start.strftime("%B %d")
            time_str = slot.start.strftime("%I:%M %p").lstrip("0")
            slot_strings.append(f"{day}, {date} at {time_str}")
        
        if len(slot_strings) == 1:
            return f"I have {slot_strings[0]} available."
        elif len(slot_strings) == 2:
            return f"I have {slot_strings[0]} or {slot_strings[1]} available."
        else:
            options = ", ".join(slot_strings[:-1]) + f", or {slot_strings[-1]}"
            return f"I have a few options: {options}. Which works best for you?"
    
    def book_appointment(
        self,
        business: Dict,
        customer: Dict,
        slot: TimeSlot,
        service_details: Dict,
        technician: Optional[Dict] = None
    ) -> BookingResult:
        """
        Book an appointment in the calendar.
        
        Args:
            business: Business profile
            customer: Customer information
            slot: Selected time slot
            service_details: Service type, notes, urgency, etc.
            technician: Assigned technician (optional)
            
        Returns:
            BookingResult with success status and details
        """
        try:
            calendar_id = None
            if business.get("calendar_integration"):
                calendar_id = business["calendar_integration"].get("google_calendar_id")
            
            if not calendar_id:
                calendar_id = "primary"
            
            customer_name = customer.get("name", "Customer")
            customer_phone = customer.get("phone_number", "")
            customer_address = customer.get("address", "")
            service_type = service_details.get("service_type", "Service Appointment")
            urgency = service_details.get("urgency_level", "normal")
            notes = service_details.get("customer_notes", "")
            
            event_title = f"{service_type} - {customer_name}"
            if urgency == "emergency":
                event_title = f"🚨 EMERGENCY: {event_title}"
            
            description_parts = [
                f"Customer: {customer_name}",
                f"Phone: {customer_phone}",
                f"Address: {customer_address}",
                f"Service: {service_type}",
                f"Urgency: {urgency}"
            ]
            if technician:
                description_parts.append(f"Technician: {technician.get('name', 'TBD')}")
            if notes:
                description_parts.append(f"Notes: {notes}")
            
            description = "\n".join(description_parts)
            
            event = {
                "summary": event_title,
                "description": description,
                "start": {
                    "dateTime": slot.start.isoformat(),
                    "timeZone": "America/New_York"
                },
                "end": {
                    "dateTime": slot.end.isoformat(),
                    "timeZone": "America/New_York"
                },
                "location": customer_address
            }
            
            google_event_id = None
            if self.calendar_service:
                try:
                    service = getattr(self.calendar_service, 'service', None)
                    if service:
                        created_event = service.events().insert(
                            calendarId=calendar_id,
                            body=event
                        ).execute()
                        google_event_id = created_event.get("id")
                except Exception as e:
                    print(f"Calendar booking error: {e}")
            
            appointment_id = f"apt_{slot.start.strftime('%Y%m%d%H%M')}_{customer_phone[-4:] if customer_phone else '0000'}"
            
            return BookingResult(
                success=True,
                appointment_id=appointment_id,
                google_event_id=google_event_id,
                message=f"Appointment booked for {slot.start.strftime('%B %d at %I:%M %p')}",
                slot=slot
            )
            
        except Exception as e:
            return BookingResult(
                success=False,
                error=str(e),
                message="Failed to book appointment"
            )
    
    def reschedule_appointment(
        self,
        business: Dict,
        original_event_id: str,
        new_slot: TimeSlot
    ) -> BookingResult:
        """Reschedule an existing appointment."""
        try:
            calendar_id = None
            if business.get("calendar_integration"):
                calendar_id = business["calendar_integration"].get("google_calendar_id")
            
            if not calendar_id:
                calendar_id = "primary"
            
            if self.calendar_service and original_event_id:
                service = getattr(self.calendar_service, 'service', None)
                if not service:
                    return BookingResult(
                        success=False,
                        error="Calendar service not connected",
                        message="Could not reschedule appointment"
                    )
                
                event = service.events().get(
                    calendarId=calendar_id,
                    eventId=original_event_id
                ).execute()
                
                event["start"]["dateTime"] = new_slot.start.isoformat()
                event["end"]["dateTime"] = new_slot.end.isoformat()
                
                updated_event = service.events().update(
                    calendarId=calendar_id,
                    eventId=original_event_id,
                    body=event
                ).execute()
                
                return BookingResult(
                    success=True,
                    appointment_id=original_event_id,
                    google_event_id=updated_event.get("id"),
                    message=f"Appointment rescheduled to {new_slot.start.strftime('%B %d at %I:%M %p')}",
                    slot=new_slot
                )
            
            return BookingResult(
                success=False,
                error="Calendar service not available",
                message="Could not reschedule appointment"
            )
            
        except Exception as e:
            return BookingResult(
                success=False,
                error=str(e),
                message="Failed to reschedule appointment"
            )
    
    def cancel_appointment(
        self,
        business: Dict,
        event_id: str,
        reason: str = ""
    ) -> Dict:
        """Cancel an appointment."""
        try:
            calendar_id = None
            if business.get("calendar_integration"):
                calendar_id = business["calendar_integration"].get("google_calendar_id")
            
            if not calendar_id:
                calendar_id = "primary"
            
            if self.calendar_service and event_id:
                service = getattr(self.calendar_service, 'service', None)
                if service:
                    service.events().delete(
                        calendarId=calendar_id,
                        eventId=event_id
                    ).execute()
                
                return {
                    "success": True,
                    "message": "Appointment cancelled successfully"
                }
            
            return {
                "success": False,
                "error": "Calendar service not available"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def parse_preferred_time(self, text: str, reference_date: Optional[datetime] = None) -> Optional[datetime]:
        """Parse natural language time preferences into datetime."""
        if reference_date is None:
            reference_date = datetime.now()
        
        text_lower = text.lower()
        
        if "today" in text_lower:
            target_date = reference_date.date()
        elif "tomorrow" in text_lower:
            target_date = (reference_date + timedelta(days=1)).date()
        elif "monday" in text_lower:
            target_date = self._next_weekday(reference_date, 0)
        elif "tuesday" in text_lower:
            target_date = self._next_weekday(reference_date, 1)
        elif "wednesday" in text_lower:
            target_date = self._next_weekday(reference_date, 2)
        elif "thursday" in text_lower:
            target_date = self._next_weekday(reference_date, 3)
        elif "friday" in text_lower:
            target_date = self._next_weekday(reference_date, 4)
        elif "saturday" in text_lower:
            target_date = self._next_weekday(reference_date, 5)
        elif "sunday" in text_lower:
            target_date = self._next_weekday(reference_date, 6)
        else:
            target_date = reference_date.date()
        
        target_time = time(9, 0)
        
        if "morning" in text_lower:
            target_time = time(9, 0)
        elif "afternoon" in text_lower:
            target_time = time(14, 0)
        elif "evening" in text_lower:
            target_time = time(17, 0)
        else:
            import re
            time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', text_lower)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2)) if time_match.group(2) else 0
                period = time_match.group(3)
                
                if period == "pm" and hour < 12:
                    hour += 12
                elif period == "am" and hour == 12:
                    hour = 0
                
                if 0 <= hour <= 23:
                    target_time = time(hour, minute)
        
        return datetime.combine(target_date, target_time)
    
    def _next_weekday(self, reference: datetime, weekday: int) -> datetime:
        """Get the next occurrence of a weekday (0=Monday)."""
        days_ahead = weekday - reference.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return (reference + timedelta(days=days_ahead)).date()


universal_appointment_engine = UniversalAppointmentEngine()
