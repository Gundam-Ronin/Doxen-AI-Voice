"""
Universal Field Extraction Engine - Dynamic field extraction based on business profile.
Extracts customer data, service details, and industry-specific fields.
"""

from openai import OpenAI
import os
import re
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


UNIVERSAL_FIELDS = [
    "name", "phone", "email", "address", "zip_code",
    "service_category", "sub_service", "job_details", "urgency",
    "preferred_date", "preferred_time", "alternate_date",
    "membership_status", "existing_customer"
]

INDUSTRY_SPECIFIC_FIELDS = {
    "hvac": ["system_type", "unit_age", "symptoms", "brand", "model", "filter_size"],
    "plumbing": ["issue_type", "fixture_type", "leak_location", "water_heater_type"],
    "electrical": ["breaker_type", "panel_age", "outlet_type", "voltage_issue"],
    "cleaning": ["home_type", "bedrooms", "bathrooms", "square_footage", "pets"],
    "pest_control": ["pest_type", "infestation_area", "severity", "previous_treatment"],
    "landscaping": ["property_size", "lawn_type", "service_frequency", "irrigation"],
    "roofing": ["roof_age", "roof_type", "leak_location", "damage_type", "stories"],
    "solar": ["roof_orientation", "energy_usage", "utility_provider", "roof_condition"],
    "locksmith": ["lock_type", "key_type", "vehicle_make_model", "locked_out"],
    "painting": ["surface_type", "room_count", "paint_type", "color_preference"],
    "pool_service": ["pool_type", "pool_size", "equipment_type", "chemical_levels"],
    "handyman": ["task_type", "materials_needed", "tools_required"],
    "moving": ["move_type", "distance", "item_count", "stairs_involved", "packing_needed"],
    "appliance_repair": ["appliance_type", "brand", "model", "error_code", "symptoms"],
    "garage_door": ["door_type", "opener_type", "issue_description", "door_age"],
    "general": ["service_description", "special_requirements"]
}


@dataclass
class ExtractionSchema:
    """Dynamic schema for field extraction based on business profile."""
    required_fields: List[str] = field(default_factory=lambda: ["name", "phone", "address"])
    optional_fields: List[str] = field(default_factory=list)
    custom_fields: List[Dict[str, Any]] = field(default_factory=list)
    industry_fields: List[str] = field(default_factory=list)
    
    @classmethod
    def from_business_profile(cls, business: Dict) -> "ExtractionSchema":
        """Create extraction schema from business profile."""
        industry = business.get("industry", "general").lower()
        
        required = ["name", "phone"]
        
        service_categories = business.get("service_categories", [])
        if service_categories:
            for cat in service_categories:
                if isinstance(cat, dict):
                    required.extend(cat.get("required_fields", []))
        
        required.extend(["address"])
        required = list(dict.fromkeys(required))
        
        optional = ["email", "zip_code", "preferred_date", "preferred_time", 
                   "job_details", "urgency", "membership_status"]
        
        industry_fields = INDUSTRY_SPECIFIC_FIELDS.get(industry, INDUSTRY_SPECIFIC_FIELDS["general"])
        
        custom_fields = business.get("custom_fields", [])
        
        return cls(
            required_fields=required,
            optional_fields=optional,
            custom_fields=custom_fields,
            industry_fields=industry_fields
        )


class UniversalFieldExtractor:
    """Extracts customer and service fields dynamically based on business configuration."""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.extracted_data: Dict[str, Any] = {}
    
    def extract_fields(
        self,
        text: str,
        schema: Optional[ExtractionSchema] = None,
        existing_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Extract fields from text using both regex patterns and AI.
        
        Args:
            text: The text to extract from
            schema: Optional extraction schema for the business
            existing_data: Previously extracted data to merge with
            
        Returns:
            Dictionary of extracted fields
        """
        if existing_data:
            self.extracted_data = existing_data.copy()
        
        self._extract_with_patterns(text)
        
        if schema:
            missing_required = [f for f in schema.required_fields if not self.extracted_data.get(f)]
            if missing_required or schema.industry_fields:
                self._extract_with_ai(text, schema)
        else:
            self._extract_with_ai(text, None)
        
        return self.extracted_data
    
    def _extract_with_patterns(self, text: str) -> None:
        """Extract common fields using regex patterns."""
        phone_pattern = r'\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b'
        phone_match = re.search(phone_pattern, text)
        if phone_match:
            phone = re.sub(r'[^\d+]', '', phone_match.group())
            if len(phone) >= 10:
                self.extracted_data["phone"] = phone
        
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        email_match = re.search(email_pattern, text, re.IGNORECASE)
        if email_match:
            self.extracted_data["email"] = email_match.group().lower()
        
        zip_pattern = r'\b\d{5}(?:-\d{4})?\b'
        zip_match = re.search(zip_pattern, text)
        if zip_match:
            self.extracted_data["zip_code"] = zip_match.group()
        
        address_patterns = [
            r'\b\d+\s+[A-Za-z]+(?:\s+[A-Za-z]+)*\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Circle|Cir|Place|Pl)\b\.?(?:\s*,?\s*(?:Apt|Suite|Unit|#)\.?\s*\w+)?',
            r'\b\d+\s+[A-Za-z\s]+,\s*[A-Za-z\s]+,?\s*[A-Z]{2}\s*\d{5}\b'
        ]
        for pattern in address_patterns:
            address_match = re.search(pattern, text, re.IGNORECASE)
            if address_match:
                self.extracted_data["address"] = address_match.group().strip()
                break
        
        date_patterns = [
            (r'\b(?:today|tomorrow|this\s+(?:morning|afternoon|evening))\b', "relative"),
            (r'\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', "weekday"),
            (r'\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b', "numeric"),
            (r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:st|nd|rd|th)?\b', "month_day")
        ]
        for pattern, date_type in date_patterns:
            date_match = re.search(pattern, text, re.IGNORECASE)
            if date_match:
                self.extracted_data["preferred_date"] = date_match.group()
                self.extracted_data["date_type"] = date_type
                break
        
        time_patterns = [
            r'\b\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)\b',
            r'\b(?:morning|afternoon|evening|noon|midnight)\b'
        ]
        for pattern in time_patterns:
            time_match = re.search(pattern, text, re.IGNORECASE)
            if time_match:
                self.extracted_data["preferred_time"] = time_match.group()
                break
        
        urgency_patterns = [
            (r'\b(?:emergency|urgent|asap|immediately|right now|critical)\b', "emergency"),
            (r'\b(?:as soon as possible|today if possible|this week)\b', "high"),
            (r'\b(?:whenever|no rush|flexible|anytime)\b', "low")
        ]
        for pattern, level in urgency_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                self.extracted_data["urgency"] = level
                break
    
    def _extract_with_ai(self, text: str, schema: Optional[ExtractionSchema]) -> None:
        """Use AI to extract fields that patterns couldn't catch."""
        try:
            if schema:
                fields_to_extract = (
                    schema.required_fields + 
                    schema.optional_fields + 
                    schema.industry_fields
                )
                custom_field_names = [f.get("field_name", "") for f in schema.custom_fields]
                fields_to_extract.extend(custom_field_names)
            else:
                fields_to_extract = UNIVERSAL_FIELDS + INDUSTRY_SPECIFIC_FIELDS["general"]
            
            already_extracted = list(self.extracted_data.keys())
            fields_needed = [f for f in fields_to_extract if f not in already_extracted]
            
            if not fields_needed:
                return
            
            field_descriptions = {
                "name": "Customer's full name",
                "phone": "Phone number",
                "email": "Email address",
                "address": "Street address",
                "zip_code": "ZIP/postal code",
                "service_category": "Type of service needed (e.g., repair, installation, maintenance)",
                "sub_service": "Specific service within category",
                "job_details": "Description of the issue or work needed",
                "urgency": "Urgency level (emergency/high/normal/low)",
                "preferred_date": "Preferred appointment date",
                "preferred_time": "Preferred appointment time",
                "system_type": "Type of system/equipment",
                "symptoms": "Symptoms or issues described",
                "brand": "Brand/manufacturer name",
                "issue_type": "Type of issue/problem"
            }
            
            fields_prompt = "\n".join([
                f"- {f}: {field_descriptions.get(f, f.replace('_', ' ').title())}"
                for f in fields_needed[:15]
            ])
            
            prompt = f"""Extract the following information from this customer statement if mentioned.
Only include fields that are clearly stated or strongly implied.

Customer said: "{text}"

Fields to extract:
{fields_prompt}

Respond with JSON only. Use null for fields not found:
{{"field_name": "value or null", ...}}"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                max_tokens=300,
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            
            for key, value in result.items():
                if value and value != "null" and key not in self.extracted_data:
                    self.extracted_data[key] = value
                    
        except Exception as e:
            print(f"AI field extraction error: {e}")
    
    def get_missing_required_fields(self, schema: ExtractionSchema) -> List[str]:
        """Get list of required fields that haven't been extracted yet."""
        return [f for f in schema.required_fields if not self.extracted_data.get(f)]
    
    def generate_collection_prompt(
        self,
        missing_fields: List[str],
        business_name: str = "our company"
    ) -> str:
        """Generate a natural prompt to collect missing information."""
        if not missing_fields:
            return ""
        
        field_prompts = {
            "name": "May I have your name?",
            "phone": "What's the best phone number to reach you?",
            "email": "What's your email address?",
            "address": "What's the address where you need service?",
            "zip_code": "What's your ZIP code?",
            "service_category": "What type of service do you need?",
            "job_details": "Can you describe what's going on?",
            "preferred_date": "When would you like us to come out?",
            "preferred_time": "Do you have a preferred time?"
        }
        
        if len(missing_fields) == 1:
            return field_prompts.get(missing_fields[0], f"Could you provide your {missing_fields[0].replace('_', ' ')}?")
        
        if len(missing_fields) == 2:
            prompts = [field_prompts.get(f, f.replace('_', ' ')) for f in missing_fields[:2]]
            return f"{prompts[0]} And {prompts[1].lower()}"
        
        first_field = missing_fields[0]
        return field_prompts.get(first_field, f"I'll need a few details. First, could you tell me your {first_field.replace('_', ' ')}?")
    
    def merge_data(self, new_data: Dict[str, Any]) -> Dict[str, Any]:
        """Merge new extracted data with existing data."""
        for key, value in new_data.items():
            if value and not self.extracted_data.get(key):
                self.extracted_data[key] = value
        return self.extracted_data
    
    def reset(self) -> None:
        """Reset extracted data for a new call."""
        self.extracted_data = {}
    
    def to_customer_record(self) -> Dict[str, Any]:
        """Convert extracted data to a customer record format."""
        return {
            "name": self.extracted_data.get("name"),
            "phone_number": self.extracted_data.get("phone"),
            "email": self.extracted_data.get("email"),
            "address": self.extracted_data.get("address"),
            "zip_code": self.extracted_data.get("zip_code"),
            "extra_data": {
                k: v for k, v in self.extracted_data.items()
                if k not in ["name", "phone", "email", "address", "zip_code"]
            }
        }


universal_field_extractor = UniversalFieldExtractor()
