"""
Phase 7.2 - Advanced Appointment Engine
Commercial-grade scheduling with buffer times, travel rules, technician shifts,
peak pricing, multi-day jobs, two-tech jobs, weekend logic, and urgency routing.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta, time
from enum import Enum
import json


class UrgencyLevel(Enum):
    NORMAL = "normal"
    HIGH = "high"
    EMERGENCY = "emergency"
    SAME_DAY = "same_day"


class JobType(Enum):
    STANDARD = "standard"
    MULTI_DAY = "multi_day"
    TWO_TECH = "two_tech"
    INSPECTION = "inspection"
    EMERGENCY = "emergency"


@dataclass
class TimeSlot:
    start: datetime
    end: datetime
    technician_id: Optional[int] = None
    technician_name: Optional[str] = None
    is_peak: bool = False
    price_multiplier: float = 1.0
    travel_time_minutes: int = 0
    buffer_before: int = 0
    buffer_after: int = 0


@dataclass
class TechnicianShift:
    technician_id: int
    start_time: time
    end_time: time
    break_start: Optional[time] = None
    break_end: Optional[time] = None
    max_jobs_per_day: int = 8
    current_jobs: int = 0


@dataclass
class JobRequirements:
    service_type: str
    estimated_duration: int = 60
    job_type: JobType = JobType.STANDARD
    urgency: UrgencyLevel = UrgencyLevel.NORMAL
    required_skills: List[str] = field(default_factory=list)
    required_techs: int = 1
    days_needed: int = 1
    equipment_needed: List[str] = field(default_factory=list)
    customer_zip: Optional[str] = None


@dataclass
class BookingResult:
    success: bool
    slots: List[TimeSlot] = field(default_factory=list)
    message: str = ""
    total_price: Optional[float] = None
    assigned_technicians: List[Dict] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class AdvancedAppointmentEngine:
    """Commercial-grade appointment scheduling engine."""
    
    def __init__(self):
        self.default_buffer_minutes = 15
        self.default_travel_minutes = 30
        self.max_travel_minutes = 60
        
        self.peak_hours = {
            "morning": (time(8, 0), time(10, 0)),
            "evening": (time(16, 0), time(18, 0))
        }
        self.peak_multiplier = 1.25
        
        self.weekend_multiplier = 1.5
        self.emergency_multiplier = 2.0
        self.same_day_multiplier = 1.35
        
        self.default_shift = TechnicianShift(
            technician_id=0,
            start_time=time(8, 0),
            end_time=time(17, 0),
            break_start=time(12, 0),
            break_end=time(13, 0)
        )
        
        self.min_slot_duration = 30
        self.max_advance_days = 90
    
    def get_available_slots(
        self,
        business: Dict[str, Any],
        job_requirements: JobRequirements,
        technicians: List[Dict],
        existing_appointments: List[Dict],
        start_date: datetime = None,
        days_to_check: int = 7
    ) -> List[TimeSlot]:
        """Get available time slots considering all constraints."""
        start_date = start_date or datetime.now()
        available_slots = []
        
        business_hours = business.get("business_hours", {})
        
        for day_offset in range(days_to_check):
            check_date = start_date + timedelta(days=day_offset)
            
            if job_requirements.urgency != UrgencyLevel.EMERGENCY:
                if check_date.date() == start_date.date() and datetime.now().hour >= 15:
                    continue
            
            day_slots = self._get_day_slots(
                check_date,
                business_hours,
                job_requirements,
                technicians,
                existing_appointments
            )
            available_slots.extend(day_slots)
        
        return self._prioritize_slots(available_slots, job_requirements)
    
    def _get_day_slots(
        self,
        date: datetime,
        business_hours: Dict,
        job_requirements: JobRequirements,
        technicians: List[Dict],
        existing_appointments: List[Dict]
    ) -> List[TimeSlot]:
        """Get available slots for a specific day."""
        day_name = date.strftime("%a").lower()
        hours = business_hours.get(day_name, [])
        
        if not hours:
            return []
        
        slots = []
        is_weekend = date.weekday() >= 5
        
        for tech in technicians:
            if not tech.get("is_available", True):
                continue
            
            tech_shift = self._get_technician_shift(tech, date)
            if not tech_shift:
                continue
            
            tech_appointments = [
                apt for apt in existing_appointments
                if apt.get("technician_id") == tech.get("id")
                and apt.get("start_time", datetime.min).date() == date.date()
            ]
            
            if len(tech_appointments) >= tech_shift.max_jobs_per_day:
                continue
            
            day_slots = self._find_available_windows(
                date,
                tech_shift,
                tech_appointments,
                job_requirements,
                tech
            )
            
            for slot in day_slots:
                slot.technician_id = tech.get("id")
                slot.technician_name = tech.get("name")
                slot.is_peak = self._is_peak_time(slot.start.time())
                slot.price_multiplier = self._calculate_price_multiplier(
                    slot, is_weekend, job_requirements.urgency
                )
                slots.append(slot)
        
        return slots
    
    def _get_technician_shift(self, tech: Dict, date: datetime) -> Optional[TechnicianShift]:
        """Get technician's shift for a specific date."""
        availability = tech.get("availability", {})
        day_name = date.strftime("%a").lower()
        
        day_hours = availability.get(day_name, availability.get("default", ["08:00-17:00"]))
        
        if not day_hours:
            return None
        
        try:
            hours_str = day_hours[0] if isinstance(day_hours, list) else day_hours
            start_str, end_str = hours_str.split("-")
            start_time = time.fromisoformat(start_str)
            end_time = time.fromisoformat(end_str)
            
            return TechnicianShift(
                technician_id=tech.get("id", 0),
                start_time=start_time,
                end_time=end_time,
                max_jobs_per_day=tech.get("max_jobs_per_day", 8)
            )
        except Exception:
            return self.default_shift
    
    def _find_available_windows(
        self,
        date: datetime,
        shift: TechnicianShift,
        existing_appointments: List[Dict],
        job_requirements: JobRequirements,
        tech: Dict
    ) -> List[TimeSlot]:
        """Find available time windows within a shift."""
        slots = []
        duration = job_requirements.estimated_duration
        buffer = self.default_buffer_minutes
        travel = self._estimate_travel_time(tech, job_requirements.customer_zip)
        
        sorted_appointments = sorted(
            existing_appointments,
            key=lambda x: x.get("start_time", datetime.min)
        )
        
        shift_start = datetime.combine(date.date(), shift.start_time)
        shift_end = datetime.combine(date.date(), shift.end_time)
        
        current_time = shift_start
        
        if date.date() == datetime.now().date():
            now_plus_buffer = datetime.now() + timedelta(minutes=30)
            if now_plus_buffer > current_time:
                current_time = now_plus_buffer
        
        for apt in sorted_appointments:
            apt_start = apt.get("start_time")
            apt_end = apt.get("end_time")
            
            if isinstance(apt_start, str):
                apt_start = datetime.fromisoformat(apt_start)
            if isinstance(apt_end, str):
                apt_end = datetime.fromisoformat(apt_end)
            
            if not apt_start or not apt_end:
                continue
            
            apt_start_with_buffer = apt_start - timedelta(minutes=buffer)
            
            available_minutes = (apt_start_with_buffer - current_time).total_seconds() / 60
            
            if available_minutes >= duration + travel:
                slot_start = current_time + timedelta(minutes=travel)
                slot_end = slot_start + timedelta(minutes=duration)
                
                if shift.break_start and shift.break_end:
                    break_start = datetime.combine(date.date(), shift.break_start)
                    break_end = datetime.combine(date.date(), shift.break_end)
                    
                    if not (slot_start < break_end and slot_end > break_start):
                        slots.append(TimeSlot(
                            start=slot_start,
                            end=slot_end,
                            travel_time_minutes=travel,
                            buffer_before=buffer,
                            buffer_after=buffer
                        ))
                else:
                    slots.append(TimeSlot(
                        start=slot_start,
                        end=slot_end,
                        travel_time_minutes=travel,
                        buffer_before=buffer,
                        buffer_after=buffer
                    ))
            
            current_time = apt_end + timedelta(minutes=buffer)
        
        available_minutes = (shift_end - current_time).total_seconds() / 60
        if available_minutes >= duration + travel:
            slot_start = current_time + timedelta(minutes=travel)
            slot_end = slot_start + timedelta(minutes=duration)
            
            if slot_end <= shift_end:
                slots.append(TimeSlot(
                    start=slot_start,
                    end=slot_end,
                    travel_time_minutes=travel,
                    buffer_before=buffer,
                    buffer_after=buffer
                ))
        
        return slots
    
    def _estimate_travel_time(self, tech: Dict, customer_zip: str) -> int:
        """Estimate travel time between technician and customer."""
        if not customer_zip:
            return self.default_travel_minutes
        
        tech_zip = tech.get("home_zip", "")
        
        if not tech_zip:
            return self.default_travel_minutes
        
        if tech_zip[:3] == customer_zip[:3]:
            return 15
        elif tech_zip[:2] == customer_zip[:2]:
            return 25
        else:
            return self.default_travel_minutes
    
    def _is_peak_time(self, check_time: time) -> bool:
        """Check if a time falls within peak hours."""
        for period_name, (start, end) in self.peak_hours.items():
            if start <= check_time <= end:
                return True
        return False
    
    def _calculate_price_multiplier(
        self,
        slot: TimeSlot,
        is_weekend: bool,
        urgency: UrgencyLevel
    ) -> float:
        """Calculate price multiplier based on various factors."""
        multiplier = 1.0
        
        if is_weekend:
            multiplier *= self.weekend_multiplier
        
        if slot.is_peak:
            multiplier *= self.peak_multiplier
        
        if urgency == UrgencyLevel.EMERGENCY:
            multiplier *= self.emergency_multiplier
        elif urgency == UrgencyLevel.SAME_DAY:
            multiplier *= self.same_day_multiplier
        
        return round(multiplier, 2)
    
    def _prioritize_slots(
        self,
        slots: List[TimeSlot],
        job_requirements: JobRequirements
    ) -> List[TimeSlot]:
        """Prioritize and sort available slots."""
        if job_requirements.urgency in [UrgencyLevel.EMERGENCY, UrgencyLevel.SAME_DAY]:
            slots.sort(key=lambda s: (s.start, s.price_multiplier))
        else:
            slots.sort(key=lambda s: (s.price_multiplier, s.start))
        
        return slots
    
    def book_multi_day_job(
        self,
        business: Dict,
        job_requirements: JobRequirements,
        technicians: List[Dict],
        existing_appointments: List[Dict],
        start_date: datetime
    ) -> BookingResult:
        """Book a multi-day job."""
        days_needed = job_requirements.days_needed
        consecutive_slots = []
        warnings = []
        
        for day_offset in range(days_needed):
            check_date = start_date + timedelta(days=day_offset)
            
            if check_date.weekday() >= 5:
                start_date = start_date + timedelta(days=1)
                warnings.append(f"Skipped weekend day, adjusted to {start_date.strftime('%A')}")
                continue
            
            day_slots = self._get_day_slots(
                check_date,
                business.get("business_hours", {}),
                job_requirements,
                technicians,
                existing_appointments
            )
            
            if not day_slots:
                return BookingResult(
                    success=False,
                    message=f"No availability on {check_date.strftime('%A, %B %d')}",
                    warnings=warnings
                )
            
            consecutive_slots.append(day_slots[0])
        
        return BookingResult(
            success=True,
            slots=consecutive_slots,
            message=f"Multi-day job booked for {days_needed} days starting {start_date.strftime('%B %d')}",
            assigned_technicians=[{"id": s.technician_id, "name": s.technician_name} for s in consecutive_slots],
            warnings=warnings
        )
    
    def book_two_tech_job(
        self,
        business: Dict,
        job_requirements: JobRequirements,
        technicians: List[Dict],
        existing_appointments: List[Dict],
        preferred_date: datetime = None
    ) -> BookingResult:
        """Book a job requiring two technicians."""
        preferred_date = preferred_date or datetime.now() + timedelta(days=1)
        
        all_slots = self.get_available_slots(
            business,
            job_requirements,
            technicians,
            existing_appointments,
            preferred_date,
            days_to_check=14
        )
        
        slot_by_time: Dict[str, List[TimeSlot]] = {}
        for slot in all_slots:
            time_key = slot.start.isoformat()
            if time_key not in slot_by_time:
                slot_by_time[time_key] = []
            slot_by_time[time_key].append(slot)
        
        for time_key, slots in slot_by_time.items():
            if len(slots) >= 2:
                two_slots = slots[:2]
                return BookingResult(
                    success=True,
                    slots=two_slots,
                    message=f"Two-technician job booked for {two_slots[0].start.strftime('%B %d at %I:%M %p')}",
                    assigned_technicians=[
                        {"id": s.technician_id, "name": s.technician_name}
                        for s in two_slots
                    ]
                )
        
        return BookingResult(
            success=False,
            message="Unable to find a time slot with two available technicians in the next 14 days"
        )
    
    def handle_emergency_routing(
        self,
        business: Dict,
        technicians: List[Dict],
        existing_appointments: List[Dict],
        customer_zip: str = None
    ) -> BookingResult:
        """Route emergency calls to the nearest available technician."""
        now = datetime.now()
        
        available_techs = []
        for tech in technicians:
            if not tech.get("is_available", True):
                continue
            if tech.get("status") not in ["active", "available"]:
                continue
            
            today_appointments = [
                apt for apt in existing_appointments
                if apt.get("technician_id") == tech.get("id")
                and apt.get("start_time", datetime.min).date() == now.date()
            ]
            
            current_job = None
            for apt in today_appointments:
                apt_start = apt.get("start_time")
                apt_end = apt.get("end_time")
                if isinstance(apt_start, str):
                    apt_start = datetime.fromisoformat(apt_start)
                if isinstance(apt_end, str):
                    apt_end = datetime.fromisoformat(apt_end)
                
                if apt_start <= now <= apt_end:
                    current_job = apt
                    break
            
            travel_time = self._estimate_travel_time(tech, customer_zip)
            
            available_techs.append({
                "tech": tech,
                "is_busy": current_job is not None,
                "current_job": current_job,
                "travel_time": travel_time,
                "jobs_today": len(today_appointments)
            })
        
        available_techs.sort(key=lambda x: (x["is_busy"], x["travel_time"], x["jobs_today"]))
        
        if not available_techs:
            return BookingResult(
                success=False,
                message="No technicians available for emergency dispatch"
            )
        
        best_tech = available_techs[0]
        eta = now + timedelta(minutes=best_tech["travel_time"])
        
        if best_tech["is_busy"]:
            eta = eta + timedelta(minutes=30)
        
        emergency_slot = TimeSlot(
            start=eta,
            end=eta + timedelta(hours=2),
            technician_id=best_tech["tech"].get("id"),
            technician_name=best_tech["tech"].get("name"),
            is_peak=False,
            price_multiplier=self.emergency_multiplier,
            travel_time_minutes=best_tech["travel_time"]
        )
        
        message = f"Emergency dispatch: {best_tech['tech'].get('name')} will arrive by {eta.strftime('%I:%M %p')}"
        if best_tech["is_busy"]:
            message += " (after completing current job)"
        
        return BookingResult(
            success=True,
            slots=[emergency_slot],
            message=message,
            assigned_technicians=[{
                "id": best_tech["tech"].get("id"),
                "name": best_tech["tech"].get("name"),
                "phone": best_tech["tech"].get("phone"),
                "eta": eta.isoformat()
            }]
        )
    
    def calculate_job_price(
        self,
        base_price: float,
        slot: TimeSlot,
        job_requirements: JobRequirements
    ) -> Dict[str, Any]:
        """Calculate final job price with all multipliers."""
        breakdown = {
            "base_price": base_price,
            "multipliers": [],
            "additional_fees": []
        }
        
        final_price = base_price
        
        if slot.price_multiplier != 1.0:
            final_price *= slot.price_multiplier
            
            if slot.start.weekday() >= 5:
                breakdown["multipliers"].append({
                    "name": "Weekend Service",
                    "multiplier": self.weekend_multiplier
                })
            
            if slot.is_peak:
                breakdown["multipliers"].append({
                    "name": "Peak Hours",
                    "multiplier": self.peak_multiplier
                })
        
        if job_requirements.urgency == UrgencyLevel.EMERGENCY:
            breakdown["multipliers"].append({
                "name": "Emergency Service",
                "multiplier": self.emergency_multiplier
            })
        elif job_requirements.urgency == UrgencyLevel.SAME_DAY:
            breakdown["multipliers"].append({
                "name": "Same-Day Service",
                "multiplier": self.same_day_multiplier
            })
        
        if job_requirements.required_techs > 1:
            tech_fee = base_price * 0.5 * (job_requirements.required_techs - 1)
            final_price += tech_fee
            breakdown["additional_fees"].append({
                "name": f"Additional Technician(s) ({job_requirements.required_techs - 1})",
                "amount": tech_fee
            })
        
        if job_requirements.days_needed > 1:
            breakdown["additional_fees"].append({
                "name": f"Multi-Day Job ({job_requirements.days_needed} days)",
                "note": "Price applies per day"
            })
            final_price *= job_requirements.days_needed
        
        breakdown["final_price"] = round(final_price, 2)
        
        return breakdown


advanced_appointment_engine = AdvancedAppointmentEngine()
