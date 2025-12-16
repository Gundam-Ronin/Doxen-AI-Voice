"""
Phase 8.2 - AI Quote Generator
Generates quotes and estimates based on customer information and service requirements.
"""

import os
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class QuoteType(Enum):
    INSTANT = "instant"
    RANGE = "range"
    REQUIRES_INSPECTION = "requires_inspection"
    CUSTOM = "custom"


@dataclass
class QuoteLineItem:
    description: str
    quantity: int = 1
    unit_price: float = 0.0
    total: float = 0.0
    is_optional: bool = False
    notes: str = ""


@dataclass
class GeneratedQuote:
    quote_id: str
    quote_type: QuoteType
    customer_name: str
    service_type: str
    line_items: List[QuoteLineItem] = field(default_factory=list)
    subtotal: float = 0.0
    tax: float = 0.0
    discount: float = 0.0
    total: float = 0.0
    low_estimate: Optional[float] = None
    high_estimate: Optional[float] = None
    valid_until: Optional[datetime] = None
    notes: str = ""
    terms: str = ""
    confidence_level: str = "medium"
    ai_reasoning: str = ""


class QuoteGenerator:
    """AI-powered quote generation for home services."""
    
    def __init__(self):
        self.industry_pricing: Dict[str, Dict] = {}
        self._load_default_pricing()
        
        self.tax_rate = 0.0825
        self.markup_percentage = 0.20
    
    def _load_default_pricing(self):
        """Load default pricing templates by industry."""
        
        self.industry_pricing["hvac"] = {
            "service_call": {"base": 89, "range": (79, 129)},
            "diagnostic": {"base": 89, "range": (49, 129)},
            "ac_repair": {"base": 350, "range": (150, 800)},
            "ac_recharge": {"base": 275, "range": (200, 400)},
            "capacitor_replacement": {"base": 225, "range": (175, 350)},
            "blower_motor": {"base": 450, "range": (350, 650)},
            "compressor_replacement": {"base": 1800, "range": (1200, 2500)},
            "ac_installation": {"base": 5500, "range": (3500, 12000)},
            "furnace_repair": {"base": 300, "range": (150, 700)},
            "furnace_installation": {"base": 4500, "range": (2500, 8000)},
            "duct_cleaning": {"base": 450, "range": (300, 700)},
            "thermostat_installation": {"base": 275, "range": (150, 500)},
            "tune_up": {"base": 149, "range": (99, 199)},
            "emergency_fee": {"base": 150, "range": (100, 250)},
        }
        
        self.industry_pricing["plumbing"] = {
            "service_call": {"base": 89, "range": (69, 129)},
            "diagnostic": {"base": 89, "range": (49, 129)},
            "drain_cleaning": {"base": 175, "range": (99, 350)},
            "toilet_repair": {"base": 175, "range": (100, 300)},
            "toilet_replacement": {"base": 450, "range": (300, 800)},
            "faucet_repair": {"base": 150, "range": (75, 250)},
            "faucet_replacement": {"base": 275, "range": (175, 450)},
            "water_heater_repair": {"base": 225, "range": (150, 400)},
            "water_heater_installation": {"base": 1500, "range": (900, 2500)},
            "tankless_water_heater": {"base": 3500, "range": (2500, 5500)},
            "leak_repair": {"base": 275, "range": (150, 600)},
            "slab_leak_repair": {"base": 2500, "range": (1500, 4500)},
            "sewer_line_repair": {"base": 3500, "range": (1500, 8000)},
            "repiping": {"base": 8000, "range": (4000, 15000)},
            "garbage_disposal": {"base": 350, "range": (200, 550)},
            "emergency_fee": {"base": 150, "range": (100, 250)},
        }
        
        self.industry_pricing["electrical"] = {
            "service_call": {"base": 99, "range": (79, 149)},
            "diagnostic": {"base": 99, "range": (69, 149)},
            "outlet_repair": {"base": 150, "range": (75, 250)},
            "outlet_installation": {"base": 175, "range": (100, 300)},
            "gfci_installation": {"base": 200, "range": (125, 325)},
            "switch_repair": {"base": 150, "range": (75, 250)},
            "switch_installation": {"base": 175, "range": (100, 300)},
            "ceiling_fan_installation": {"base": 250, "range": (150, 450)},
            "light_fixture": {"base": 200, "range": (100, 400)},
            "recessed_lighting": {"base": 225, "range": (150, 350)},
            "panel_upgrade": {"base": 2500, "range": (1500, 4500)},
            "circuit_breaker": {"base": 225, "range": (150, 400)},
            "whole_house_surge": {"base": 450, "range": (300, 700)},
            "ev_charger": {"base": 1200, "range": (800, 2500)},
            "rewiring": {"base": 10000, "range": (6000, 20000)},
            "emergency_fee": {"base": 175, "range": (125, 275)},
        }
        
        self.industry_pricing["cleaning"] = {
            "standard_clean": {"base": 150, "range": (100, 250)},
            "deep_clean": {"base": 300, "range": (200, 500)},
            "move_in_clean": {"base": 350, "range": (250, 600)},
            "move_out_clean": {"base": 350, "range": (250, 600)},
            "post_construction": {"base": 500, "range": (300, 1000)},
            "office_cleaning": {"base": 200, "range": (100, 500)},
            "carpet_cleaning": {"base": 150, "range": (75, 300)},
            "window_cleaning": {"base": 200, "range": (100, 400)},
            "hourly_rate": {"base": 45, "range": (30, 75)},
        }
        
        self.industry_pricing["pest_control"] = {
            "inspection": {"base": 75, "range": (0, 150)},
            "general_treatment": {"base": 175, "range": (100, 300)},
            "ant_treatment": {"base": 175, "range": (100, 300)},
            "roach_treatment": {"base": 200, "range": (125, 350)},
            "termite_inspection": {"base": 100, "range": (50, 200)},
            "termite_treatment": {"base": 1500, "range": (800, 3000)},
            "bed_bug_treatment": {"base": 500, "range": (300, 1500)},
            "rodent_control": {"base": 250, "range": (150, 500)},
            "mosquito_treatment": {"base": 150, "range": (75, 300)},
            "wildlife_removal": {"base": 350, "range": (200, 800)},
            "quarterly_plan": {"base": 125, "range": (75, 200)},
        }
    
    def generate_quote(
        self,
        industry: str,
        service_type: str,
        customer_data: Dict[str, Any],
        job_details: Dict[str, Any] = None
    ) -> GeneratedQuote:
        """Generate a quote based on service type and customer information."""
        job_details = job_details or {}
        
        pricing = self.industry_pricing.get(industry.lower(), {})
        service_key = self._normalize_service_key(service_type)
        service_pricing = pricing.get(service_key)
        
        if not service_pricing:
            return self._generate_inspection_required_quote(
                customer_data, service_type
            )
        
        quote_type = self._determine_quote_type(service_key, job_details)
        
        line_items = self._build_line_items(
            industry, service_key, service_pricing, job_details
        )
        
        subtotal = sum(item.total for item in line_items if not item.is_optional)
        
        discount = self._calculate_discount(customer_data, job_details)
        
        tax = (subtotal - discount) * self.tax_rate
        
        total = subtotal - discount + tax
        
        low_estimate = service_pricing["range"][0]
        high_estimate = service_pricing["range"][1]
        
        from datetime import timedelta
        import uuid
        
        return GeneratedQuote(
            quote_id=str(uuid.uuid4())[:8].upper(),
            quote_type=quote_type,
            customer_name=customer_data.get("name", "Customer"),
            service_type=service_type,
            line_items=line_items,
            subtotal=round(subtotal, 2),
            tax=round(tax, 2),
            discount=round(discount, 2),
            total=round(total, 2),
            low_estimate=low_estimate,
            high_estimate=high_estimate,
            valid_until=datetime.now() + timedelta(days=30),
            notes=self._generate_quote_notes(industry, service_key),
            terms=self._get_standard_terms(),
            confidence_level=self._assess_confidence(service_key, job_details),
            ai_reasoning=self._generate_reasoning(service_type, job_details)
        )
    
    def _normalize_service_key(self, service_type: str) -> str:
        """Normalize service type to pricing key."""
        normalized = service_type.lower().strip()
        normalized = normalized.replace(" ", "_").replace("-", "_")
        
        mappings = {
            "ac_repair": "ac_repair",
            "air_conditioning_repair": "ac_repair",
            "air_conditioner": "ac_repair",
            "hvac_repair": "ac_repair",
            "heating_repair": "furnace_repair",
            "heater_repair": "furnace_repair",
            "drain_clog": "drain_cleaning",
            "clogged_drain": "drain_cleaning",
            "slow_drain": "drain_cleaning",
            "leaky_faucet": "faucet_repair",
            "dripping_faucet": "faucet_repair",
            "no_hot_water": "water_heater_repair",
            "water_heater": "water_heater_repair",
            "outlet_not_working": "outlet_repair",
            "dead_outlet": "outlet_repair",
            "circuit_breaker_tripping": "circuit_breaker",
            "house_cleaning": "standard_clean",
            "home_cleaning": "standard_clean",
            "regular_cleaning": "standard_clean",
            "ants": "ant_treatment",
            "roaches": "roach_treatment",
            "cockroaches": "roach_treatment",
            "mice": "rodent_control",
            "rats": "rodent_control",
        }
        
        return mappings.get(normalized, normalized)
    
    def _determine_quote_type(self, service_key: str, job_details: Dict) -> QuoteType:
        """Determine the type of quote to generate."""
        complex_services = [
            "ac_installation", "furnace_installation", "repiping",
            "sewer_line_repair", "panel_upgrade", "rewiring",
            "slab_leak_repair", "termite_treatment"
        ]
        
        if service_key in complex_services:
            return QuoteType.REQUIRES_INSPECTION
        
        if job_details.get("needs_inspection"):
            return QuoteType.REQUIRES_INSPECTION
        
        if job_details.get("unknown_scope"):
            return QuoteType.RANGE
        
        return QuoteType.INSTANT
    
    def _build_line_items(
        self,
        industry: str,
        service_key: str,
        pricing: Dict,
        job_details: Dict
    ) -> List[QuoteLineItem]:
        """Build line items for the quote."""
        items = []
        
        items.append(QuoteLineItem(
            description=f"{service_key.replace('_', ' ').title()}",
            quantity=1,
            unit_price=pricing["base"],
            total=pricing["base"]
        ))
        
        industry_pricing = self.industry_pricing.get(industry.lower(), {})
        service_call = industry_pricing.get("service_call", {})
        if service_call and service_key not in ["service_call", "diagnostic"]:
            items.append(QuoteLineItem(
                description="Service Call / Trip Charge",
                quantity=1,
                unit_price=service_call.get("base", 89),
                total=service_call.get("base", 89)
            ))
        
        if job_details.get("is_emergency"):
            emergency = industry_pricing.get("emergency_fee", {"base": 150})
            items.append(QuoteLineItem(
                description="Emergency Service Fee",
                quantity=1,
                unit_price=emergency["base"],
                total=emergency["base"]
            ))
        
        if job_details.get("parts_needed"):
            for part in job_details["parts_needed"]:
                items.append(QuoteLineItem(
                    description=f"Parts: {part.get('name', 'Part')}",
                    quantity=part.get("quantity", 1),
                    unit_price=part.get("price", 0),
                    total=part.get("quantity", 1) * part.get("price", 0)
                ))
        
        items.append(QuoteLineItem(
            description="Extended Warranty (1 year parts & labor)",
            quantity=1,
            unit_price=99,
            total=99,
            is_optional=True,
            notes="Optional - Covers all parts and labor for 1 year"
        ))
        
        return items
    
    def _calculate_discount(self, customer_data: Dict, job_details: Dict) -> float:
        """Calculate any applicable discounts."""
        discount = 0.0
        
        if customer_data.get("customer_type") == "vip":
            discount += 50
        
        if customer_data.get("is_returning"):
            discount += 25
        
        if job_details.get("promo_code"):
            promo_discounts = {
                "SAVE10": 0.10,
                "FIRST50": 50,
                "SUMMER20": 0.20,
            }
            promo = job_details["promo_code"].upper()
            if promo in promo_discounts:
                promo_value = promo_discounts[promo]
                if isinstance(promo_value, float):
                    pass
                else:
                    discount += promo_value
        
        return discount
    
    def _generate_quote_notes(self, industry: str, service_key: str) -> str:
        """Generate notes for the quote."""
        notes = [
            "Quote includes standard labor and materials.",
            "Price may vary based on actual conditions found on-site.",
        ]
        
        if industry == "hvac":
            notes.append("All HVAC work includes system inspection and testing.")
        elif industry == "plumbing":
            notes.append("Permit fees, if required, are not included.")
        elif industry == "electrical":
            notes.append("All electrical work is performed to code by licensed electricians.")
        
        return " ".join(notes)
    
    def _get_standard_terms(self) -> str:
        """Get standard quote terms."""
        return (
            "Quote valid for 30 days. "
            "50% deposit required to schedule. "
            "Balance due upon completion. "
            "All work guaranteed for 30 days."
        )
    
    def _assess_confidence(self, service_key: str, job_details: Dict) -> str:
        """Assess confidence level of the quote."""
        if job_details.get("detailed_description"):
            return "high"
        if job_details.get("unknown_scope"):
            return "low"
        return "medium"
    
    def _generate_reasoning(self, service_type: str, job_details: Dict) -> str:
        """Generate AI reasoning for the quote."""
        reasoning = f"Quote generated for {service_type}. "
        
        if job_details.get("is_emergency"):
            reasoning += "Emergency service fee applied due to urgency. "
        
        if job_details.get("complexity") == "high":
            reasoning += "Higher estimate due to job complexity. "
        
        return reasoning
    
    def _generate_inspection_required_quote(
        self,
        customer_data: Dict,
        service_type: str
    ) -> GeneratedQuote:
        """Generate a quote that requires on-site inspection."""
        import uuid
        
        return GeneratedQuote(
            quote_id=str(uuid.uuid4())[:8].upper(),
            quote_type=QuoteType.REQUIRES_INSPECTION,
            customer_name=customer_data.get("name", "Customer"),
            service_type=service_type,
            line_items=[
                QuoteLineItem(
                    description="On-Site Inspection & Estimate",
                    quantity=1,
                    unit_price=0,
                    total=0,
                    notes="Free estimate - no obligation"
                )
            ],
            subtotal=0,
            tax=0,
            total=0,
            notes=(
                "This service requires an on-site inspection to provide an accurate quote. "
                "Our technician will assess the work needed and provide a detailed estimate "
                "before any work begins."
            ),
            terms="Free estimate provided on-site. No obligation.",
            confidence_level="low",
            ai_reasoning=(
                f"Service '{service_type}' requires professional assessment. "
                "Pricing varies significantly based on specific conditions."
            )
        )
    
    def get_price_range(self, industry: str, service_type: str) -> Optional[tuple]:
        """Get price range for a service."""
        pricing = self.industry_pricing.get(industry.lower(), {})
        service_key = self._normalize_service_key(service_type)
        service_pricing = pricing.get(service_key)
        
        if service_pricing:
            return service_pricing["range"]
        return None
    
    def format_quote_for_voice(self, quote: GeneratedQuote) -> str:
        """Format quote for voice response."""
        if quote.quote_type == QuoteType.REQUIRES_INSPECTION:
            return (
                f"For {quote.service_type}, I'd recommend scheduling a free on-site estimate. "
                "Our technician will assess the work needed and provide you with an accurate quote. "
                "Would you like to schedule that?"
            )
        
        if quote.quote_type == QuoteType.RANGE:
            return (
                f"For {quote.service_type}, pricing typically ranges from "
                f"${quote.low_estimate} to ${quote.high_estimate}, "
                "depending on the specific work needed. "
                "Would you like to schedule service?"
            )
        
        return (
            f"For {quote.service_type}, the estimated total is ${quote.total:.2f}. "
            "This includes service call and standard labor. "
            "Would you like to schedule an appointment?"
        )


quote_generator = QuoteGenerator()
