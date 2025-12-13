import re
import json
from typing import Dict, Optional
from openai import OpenAI
import os

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def extract_customer_data_regex(text: str) -> Dict:
    """Extract customer data using regex patterns."""
    data = {
        "name": None,
        "phone": None,
        "email": None,
        "address": None
    }
    
    phone_patterns = [
        r'\b(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b',
        r'\b(\(\d{3}\)\s*\d{3}[-.\s]?\d{4})\b',
    ]
    for pattern in phone_patterns:
        match = re.search(pattern, text)
        if match:
            data["phone"] = re.sub(r'[^\d]', '', match.group(1))
            break
    
    email_pattern = r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'
    match = re.search(email_pattern, text, re.IGNORECASE)
    if match:
        data["email"] = match.group(1).lower()
    
    name_patterns = [
        r"(?:my name is|i'm|i am|this is|name's)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"(?:call me|it's)\s+([A-Z][a-z]+)",
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data["name"] = match.group(1).title()
            break
    
    address_patterns = [
        r'(\d+\s+[A-Za-z]+(?:\s+[A-Za-z]+)*\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct|Circle|Cir)\.?(?:\s*,?\s*(?:Apt|Apartment|Suite|Unit|#)\.?\s*\d+)?)',
    ]
    for pattern in address_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data["address"] = match.group(1)
            break
    
    return data


async def extract_customer_data_ai(conversation_text: str) -> Dict:
    """Use AI to extract customer information from conversation."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """Extract customer information from this phone conversation. 
Return a JSON object with these fields (use null if not found):
- name: Customer's full name
- phone: Phone number (digits only)
- email: Email address
- address: Full street address
- service_needed: What service they're requesting
- preferred_time: When they want the appointment
- urgency: "emergency", "urgent", "normal", or "flexible"

Only extract information explicitly stated. Do not guess or infer."""
                },
                {
                    "role": "user",
                    "content": conversation_text
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=500
        )
        
        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        print(f"AI extraction error: {e}")
        return extract_customer_data_regex(conversation_text)


def merge_customer_data(existing: Dict, new_data: Dict) -> Dict:
    """Merge new extracted data with existing data, preferring non-null values."""
    merged = existing.copy()
    for key, value in new_data.items():
        if value and (key not in merged or merged[key] is None):
            merged[key] = value
    return merged


class CustomerDataCollector:
    """Tracks and collects customer data throughout a call."""
    
    def __init__(self):
        self.data = {
            "name": None,
            "phone": None,
            "email": None,
            "address": None,
            "service_needed": None,
            "preferred_time": None,
            "urgency": "normal"
        }
        self.conversation_buffer = []
    
    def add_utterance(self, speaker: str, text: str):
        """Add an utterance to the conversation buffer."""
        self.conversation_buffer.append(f"{speaker}: {text}")
        
        regex_data = extract_customer_data_regex(text)
        self.data = merge_customer_data(self.data, regex_data)
    
    async def finalize_extraction(self) -> Dict:
        """Run AI extraction on full conversation to fill gaps."""
        if self.conversation_buffer:
            full_text = "\n".join(self.conversation_buffer)
            ai_data = await extract_customer_data_ai(full_text)
            self.data = merge_customer_data(self.data, ai_data)
        return self.data
    
    def get_missing_fields(self) -> list:
        """Get list of important missing fields."""
        required = ["name", "phone"]
        return [f for f in required if not self.data.get(f)]
    
    def has_booking_info(self) -> bool:
        """Check if we have enough info to book an appointment."""
        return bool(self.data.get("name") and self.data.get("phone"))
    
    def get_data(self) -> Dict:
        return self.data.copy()
