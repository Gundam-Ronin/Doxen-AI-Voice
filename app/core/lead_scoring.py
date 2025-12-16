"""
Phase 8.3 - Smart Lead Scoring Engine
ML-powered prediction for high-value customers.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import json


class LeadTier(Enum):
    HOT = "hot"
    WARM = "warm"
    COOL = "cool"
    COLD = "cold"


class CustomerType(Enum):
    HOMEOWNER = "homeowner"
    RENTER = "renter"
    PROPERTY_MANAGER = "property_manager"
    BUSINESS = "business"
    UNKNOWN = "unknown"


@dataclass
class LeadScore:
    total_score: int
    tier: LeadTier
    conversion_probability: float
    estimated_value: float
    priority_rank: int
    scoring_factors: List[Dict[str, Any]]
    recommendations: List[str]
    customer_type: CustomerType
    urgency_level: str


class LeadScoringEngine:
    """ML-inspired lead scoring for home services."""
    
    def __init__(self):
        self.base_score = 50
        self.max_score = 100
        
        self.scoring_weights = {
            "urgency": 25,
            "service_value": 20,
            "customer_type": 15,
            "location": 10,
            "timing": 10,
            "engagement": 10,
            "history": 10,
        }
        
        self.high_value_zip_prefixes = [
            "770", "771", "772", "773", "774", "775", "776", "777",
            "900", "901", "902", "903", "904", "905",
            "100", "101", "102", "103", "104",
        ]
        
        self.service_values = {
            "ac_installation": 8000,
            "furnace_installation": 6000,
            "water_heater_installation": 2000,
            "repiping": 10000,
            "panel_upgrade": 3500,
            "rewiring": 15000,
            "sewer_line": 5000,
            "ac_repair": 500,
            "plumbing_repair": 300,
            "electrical_repair": 300,
            "tune_up": 150,
            "cleaning": 200,
            "pest_control": 175,
        }
        
        self.urgency_multipliers = {
            "emergency": 2.0,
            "same_day": 1.5,
            "this_week": 1.2,
            "flexible": 1.0,
        }
    
    def score_lead(
        self,
        customer_data: Dict[str, Any],
        call_data: Dict[str, Any] = None,
        business_data: Dict[str, Any] = None
    ) -> LeadScore:
        """Score a lead based on multiple factors."""
        call_data = call_data or {}
        business_data = business_data or {}
        
        factors = []
        total_weighted_score = 0
        
        urgency_score, urgency_factors = self._score_urgency(call_data)
        factors.extend(urgency_factors)
        total_weighted_score += urgency_score * self.scoring_weights["urgency"] / 100
        
        value_score, value_factors = self._score_service_value(call_data)
        factors.extend(value_factors)
        total_weighted_score += value_score * self.scoring_weights["service_value"] / 100
        
        type_score, type_factors, customer_type = self._score_customer_type(customer_data)
        factors.extend(type_factors)
        total_weighted_score += type_score * self.scoring_weights["customer_type"] / 100
        
        location_score, location_factors = self._score_location(customer_data)
        factors.extend(location_factors)
        total_weighted_score += location_score * self.scoring_weights["location"] / 100
        
        timing_score, timing_factors = self._score_timing(call_data)
        factors.extend(timing_factors)
        total_weighted_score += timing_score * self.scoring_weights["timing"] / 100
        
        engagement_score, engagement_factors = self._score_engagement(call_data)
        factors.extend(engagement_factors)
        total_weighted_score += engagement_score * self.scoring_weights["engagement"] / 100
        
        history_score, history_factors = self._score_history(customer_data)
        factors.extend(history_factors)
        total_weighted_score += history_score * self.scoring_weights["history"] / 100
        
        final_score = int(min(self.max_score, max(0, total_weighted_score * 100)))
        
        tier = self._determine_tier(final_score)
        conversion_prob = self._calculate_conversion_probability(final_score, factors)
        estimated_value = self._estimate_customer_value(call_data, customer_data)
        urgency_level = call_data.get("urgency", "flexible")
        
        recommendations = self._generate_recommendations(
            tier, factors, customer_type, call_data
        )
        
        return LeadScore(
            total_score=final_score,
            tier=tier,
            conversion_probability=conversion_prob,
            estimated_value=estimated_value,
            priority_rank=self._calculate_priority(final_score, urgency_level, estimated_value),
            scoring_factors=factors,
            recommendations=recommendations,
            customer_type=customer_type,
            urgency_level=urgency_level
        )
    
    def _score_urgency(self, call_data: Dict) -> Tuple[float, List[Dict]]:
        """Score based on urgency signals."""
        factors = []
        score = 50
        
        urgency = call_data.get("urgency", "flexible")
        
        if urgency == "emergency":
            score = 100
            factors.append({
                "factor": "urgency",
                "signal": "Emergency service needed",
                "impact": "+50 points",
                "weight": "high"
            })
        elif urgency == "same_day":
            score = 85
            factors.append({
                "factor": "urgency",
                "signal": "Same-day service requested",
                "impact": "+35 points",
                "weight": "high"
            })
        elif urgency == "this_week":
            score = 70
            factors.append({
                "factor": "urgency",
                "signal": "Service needed this week",
                "impact": "+20 points",
                "weight": "medium"
            })
        
        is_emergency = call_data.get("is_emergency", False)
        if is_emergency and urgency != "emergency":
            score += 20
            factors.append({
                "factor": "urgency",
                "signal": "Emergency keywords detected",
                "impact": "+20 points",
                "weight": "high"
            })
        
        return score / 100, factors
    
    def _score_service_value(self, call_data: Dict) -> Tuple[float, List[Dict]]:
        """Score based on potential service value."""
        factors = []
        score = 50
        
        service_type = call_data.get("service_type", "").lower()
        
        for service_key, value in self.service_values.items():
            if service_key in service_type:
                if value >= 5000:
                    score = 100
                    factors.append({
                        "factor": "service_value",
                        "signal": f"High-value service: ${value}+",
                        "impact": "+50 points",
                        "weight": "high"
                    })
                elif value >= 1000:
                    score = 80
                    factors.append({
                        "factor": "service_value",
                        "signal": f"Mid-value service: ${value}",
                        "impact": "+30 points",
                        "weight": "medium"
                    })
                else:
                    score = 60
                    factors.append({
                        "factor": "service_value",
                        "signal": f"Standard service: ${value}",
                        "impact": "+10 points",
                        "weight": "low"
                    })
                break
        
        return score / 100, factors
    
    def _score_customer_type(self, customer_data: Dict) -> Tuple[float, List[Dict], CustomerType]:
        """Score based on customer type."""
        factors = []
        score = 50
        customer_type = CustomerType.UNKNOWN
        
        address = customer_data.get("address", "").lower()
        name = customer_data.get("name", "").lower()
        
        if "management" in name or "properties" in name or "realty" in name:
            customer_type = CustomerType.PROPERTY_MANAGER
            score = 90
            factors.append({
                "factor": "customer_type",
                "signal": "Property manager detected",
                "impact": "+40 points (repeat business potential)",
                "weight": "high"
            })
        elif any(word in address for word in ["apt", "apartment", "unit #", "suite"]):
            customer_type = CustomerType.RENTER
            score = 40
            factors.append({
                "factor": "customer_type",
                "signal": "Renter (may need landlord approval)",
                "impact": "-10 points",
                "weight": "medium"
            })
        elif any(word in name for word in ["llc", "inc", "corp", "company"]):
            customer_type = CustomerType.BUSINESS
            score = 85
            factors.append({
                "factor": "customer_type",
                "signal": "Business customer",
                "impact": "+35 points (higher ticket)",
                "weight": "high"
            })
        else:
            customer_type = CustomerType.HOMEOWNER
            score = 70
            factors.append({
                "factor": "customer_type",
                "signal": "Likely homeowner",
                "impact": "+20 points",
                "weight": "medium"
            })
        
        return score / 100, factors, customer_type
    
    def _score_location(self, customer_data: Dict) -> Tuple[float, List[Dict]]:
        """Score based on customer location."""
        factors = []
        score = 50
        
        zip_code = customer_data.get("zip_code", "")
        if not zip_code and customer_data.get("address"):
            import re
            zip_match = re.search(r'\b(\d{5})\b', customer_data.get("address", ""))
            if zip_match:
                zip_code = zip_match.group(1)
        
        if zip_code:
            prefix = zip_code[:3]
            if prefix in self.high_value_zip_prefixes:
                score = 85
                factors.append({
                    "factor": "location",
                    "signal": f"High-income area (ZIP: {zip_code})",
                    "impact": "+35 points",
                    "weight": "medium"
                })
            else:
                score = 50
                factors.append({
                    "factor": "location",
                    "signal": f"Standard area (ZIP: {zip_code})",
                    "impact": "0 points",
                    "weight": "low"
                })
        
        return score / 100, factors
    
    def _score_timing(self, call_data: Dict) -> Tuple[float, List[Dict]]:
        """Score based on call timing."""
        factors = []
        score = 50
        
        call_time = call_data.get("call_time")
        if isinstance(call_time, str):
            try:
                call_time = datetime.fromisoformat(call_time)
            except:
                call_time = datetime.now()
        elif not call_time:
            call_time = datetime.now()
        
        hour = call_time.hour
        is_weekend = call_time.weekday() >= 5
        
        if 9 <= hour <= 17 and not is_weekend:
            score = 70
            factors.append({
                "factor": "timing",
                "signal": "Business hours call",
                "impact": "+20 points",
                "weight": "low"
            })
        elif is_weekend:
            score = 80
            factors.append({
                "factor": "timing",
                "signal": "Weekend caller (homeowner likely home)",
                "impact": "+30 points",
                "weight": "medium"
            })
        elif hour >= 18 or hour < 9:
            score = 75
            factors.append({
                "factor": "timing",
                "signal": "After-hours call (motivated customer)",
                "impact": "+25 points",
                "weight": "medium"
            })
        
        return score / 100, factors
    
    def _score_engagement(self, call_data: Dict) -> Tuple[float, List[Dict]]:
        """Score based on call engagement."""
        factors = []
        score = 50
        
        duration = call_data.get("duration_seconds", 0)
        
        if duration > 180:
            score = 90
            factors.append({
                "factor": "engagement",
                "signal": f"Long call ({duration}s) - high interest",
                "impact": "+40 points",
                "weight": "high"
            })
        elif duration > 60:
            score = 70
            factors.append({
                "factor": "engagement",
                "signal": f"Good engagement ({duration}s)",
                "impact": "+20 points",
                "weight": "medium"
            })
        elif duration < 30:
            score = 30
            factors.append({
                "factor": "engagement",
                "signal": f"Short call ({duration}s) - low engagement",
                "impact": "-20 points",
                "weight": "medium"
            })
        
        if call_data.get("provided_email"):
            score += 10
            factors.append({
                "factor": "engagement",
                "signal": "Provided email address",
                "impact": "+10 points",
                "weight": "low"
            })
        
        if call_data.get("asked_about_pricing"):
            score += 15
            factors.append({
                "factor": "engagement",
                "signal": "Asked about pricing (buying signal)",
                "impact": "+15 points",
                "weight": "medium"
            })
        
        return min(score, 100) / 100, factors
    
    def _score_history(self, customer_data: Dict) -> Tuple[float, List[Dict]]:
        """Score based on customer history."""
        factors = []
        score = 50
        
        if customer_data.get("is_returning"):
            score = 85
            factors.append({
                "factor": "history",
                "signal": "Returning customer",
                "impact": "+35 points",
                "weight": "high"
            })
        
        previous_spend = customer_data.get("previous_spend", 0)
        if previous_spend > 1000:
            score += 15
            factors.append({
                "factor": "history",
                "signal": f"Previous spend: ${previous_spend}",
                "impact": "+15 points",
                "weight": "medium"
            })
        
        if customer_data.get("referred_by"):
            score += 10
            factors.append({
                "factor": "history",
                "signal": "Referred customer",
                "impact": "+10 points",
                "weight": "medium"
            })
        
        return min(score, 100) / 100, factors
    
    def _determine_tier(self, score: int) -> LeadTier:
        """Determine lead tier based on score."""
        if score >= 80:
            return LeadTier.HOT
        elif score >= 60:
            return LeadTier.WARM
        elif score >= 40:
            return LeadTier.COOL
        else:
            return LeadTier.COLD
    
    def _calculate_conversion_probability(self, score: int, factors: List[Dict]) -> float:
        """Calculate conversion probability."""
        base_prob = score / 100
        
        high_weight_count = sum(1 for f in factors if f.get("weight") == "high")
        boost = high_weight_count * 0.05
        
        return min(0.95, base_prob + boost)
    
    def _estimate_customer_value(self, call_data: Dict, customer_data: Dict) -> float:
        """Estimate potential customer lifetime value."""
        service_type = call_data.get("service_type", "").lower()
        base_value = 200
        
        for service_key, value in self.service_values.items():
            if service_key in service_type:
                base_value = value
                break
        
        if customer_data.get("customer_type") == "property_manager":
            base_value *= 5
        elif customer_data.get("is_returning"):
            base_value *= 2
        
        return base_value
    
    def _calculate_priority(self, score: int, urgency: str, value: float) -> int:
        """Calculate priority rank (1 = highest)."""
        priority_score = score
        
        if urgency == "emergency":
            priority_score += 50
        elif urgency == "same_day":
            priority_score += 30
        
        if value >= 5000:
            priority_score += 20
        elif value >= 1000:
            priority_score += 10
        
        if priority_score >= 150:
            return 1
        elif priority_score >= 120:
            return 2
        elif priority_score >= 90:
            return 3
        elif priority_score >= 60:
            return 4
        else:
            return 5
    
    def _generate_recommendations(
        self,
        tier: LeadTier,
        factors: List[Dict],
        customer_type: CustomerType,
        call_data: Dict
    ) -> List[str]:
        """Generate action recommendations for the lead."""
        recommendations = []
        
        if tier == LeadTier.HOT:
            recommendations.append("Priority follow-up within 5 minutes")
            recommendations.append("Assign to senior technician for consultation")
        elif tier == LeadTier.WARM:
            recommendations.append("Follow up within 1 hour")
            recommendations.append("Send quote and scheduling options")
        elif tier == LeadTier.COOL:
            recommendations.append("Add to nurture sequence")
            recommendations.append("Schedule follow-up call for next week")
        else:
            recommendations.append("Add to general marketing list")
        
        if customer_type == CustomerType.PROPERTY_MANAGER:
            recommendations.append("Offer multi-property discount")
            recommendations.append("Propose maintenance contract")
        
        if call_data.get("is_emergency"):
            recommendations.insert(0, "URGENT: Dispatch immediately if possible")
        
        return recommendations


lead_scoring_engine = LeadScoringEngine()
