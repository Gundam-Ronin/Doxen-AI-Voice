from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from ..database.models import Technician, CallLog


class TechnicianMatcher:
    def __init__(self):
        pass
    
    def find_best_match(
        self,
        db: Session,
        business_id: int,
        service_type: Optional[str] = None,
        is_emergency: bool = False,
        skills_required: Optional[List[str]] = None
    ) -> Optional[Dict]:
        query = db.query(Technician).filter(
            Technician.business_id == business_id,
            Technician.is_available == True
        )
        
        technicians = query.all()
        
        if not technicians:
            return None
        
        scored_techs = []
        
        for tech in technicians:
            score = 100
            
            if skills_required and tech.skills:
                tech_skills_lower = [s.lower() for s in tech.skills]
                matched_skills = sum(1 for s in skills_required if s.lower() in tech_skills_lower)
                if matched_skills > 0:
                    score += matched_skills * 50
            
            if service_type and tech.skills:
                tech_skills_lower = [s.lower() for s in tech.skills]
                if service_type.lower() in tech_skills_lower:
                    score += 100
                for skill in tech_skills_lower:
                    if service_type.lower() in skill:
                        score += 50
                        break
            
            if is_emergency:
                if tech.role and "senior" in tech.role.lower():
                    score += 75
                if tech.role and "lead" in tech.role.lower():
                    score += 50
            
            scored_techs.append((tech, score))
        
        scored_techs.sort(key=lambda x: x[1], reverse=True)
        best_tech = scored_techs[0][0]
        
        return {
            "id": best_tech.id,
            "name": best_tech.name,
            "phone": best_tech.phone,
            "role": best_tech.role,
            "skills": best_tech.skills,
            "score": scored_techs[0][1]
        }
    
    def get_available_technicians(
        self,
        db: Session,
        business_id: int
    ) -> List[Dict]:
        technicians = db.query(Technician).filter(
            Technician.business_id == business_id,
            Technician.is_available == True
        ).all()
        
        return [
            {
                "id": t.id,
                "name": t.name,
                "phone": t.phone,
                "role": t.role,
                "skills": t.skills
            }
            for t in technicians
        ]
    
    def mark_technician_busy(
        self,
        db: Session,
        technician_id: int
    ) -> bool:
        tech = db.query(Technician).filter(Technician.id == technician_id).first()
        if tech:
            tech.is_available = False
            db.commit()
            return True
        return False
    
    def mark_technician_available(
        self,
        db: Session,
        technician_id: int
    ) -> bool:
        tech = db.query(Technician).filter(Technician.id == technician_id).first()
        if tech:
            tech.is_available = True
            db.commit()
            return True
        return False
    
    def auto_assign_for_call(
        self,
        db: Session,
        call_id: int,
        service_type: Optional[str] = None,
        is_emergency: bool = False
    ) -> Optional[Dict]:
        call = db.query(CallLog).filter(CallLog.id == call_id).first()
        if not call:
            return None
        
        match = self.find_best_match(
            db,
            business_id=call.business_id,
            service_type=service_type or call.service_requested,
            is_emergency=is_emergency or call.is_emergency
        )
        
        if match:
            call.assigned_tech_id = match["id"]
            db.commit()
            return match
        
        return None


technician_matcher = TechnicianMatcher()
