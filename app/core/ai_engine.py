import os
import json
from typing import Optional, Dict, Any

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = None

def get_openai_client():
    global client
    if client is None and OPENAI_API_KEY:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
    return client

async def generate_ai_response(
    user_message: str,
    business_context: Dict[str, Any],
    conversation_history: list,
    knowledgebase_context: str = "",
    personality: str = "friendly and professional"
) -> str:
    system_prompt = f"""You are Cortana, an AI voice assistant for {business_context.get('name', 'this business')}.
    
Your personality: {personality}

Business Information:
- Name: {business_context.get('name', 'N/A')}
- Services: {json.dumps(business_context.get('services', []))}
- Pricing: {json.dumps(business_context.get('pricing', {}))}
- Hours: {json.dumps(business_context.get('hours', {}))}
- Location: {business_context.get('location', 'N/A')}

Relevant Knowledge Base Information:
{knowledgebase_context}

Guidelines:
1. Be helpful, concise, and professional
2. Answer questions about services, pricing, and availability
3. Offer to book appointments when appropriate
4. Detect emergencies (water leaks, gas smells, no heat/AC) and prioritize them
5. If you detect Spanish, respond in Spanish
6. Never make up information not in the knowledge base
7. If unsure, offer to have someone call back
8. Always confirm appointment details before booking
"""

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history[-10:])
    messages.append({"role": "user", "content": user_message})
    
    openai_client = get_openai_client()
    if not openai_client:
        return "I apologize, our AI service is temporarily unavailable. Would you like me to have someone call you back?"
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"AI Engine Error: {e}")
        return "I apologize, I'm having trouble processing your request. Would you like me to have someone call you back?"

def detect_language(text: str) -> str:
    spanish_indicators = ['hola', 'gracias', 'necesito', 'quiero', 'ayuda', 'por favor', 'buenos', 'buenas']
    text_lower = text.lower()
    for indicator in spanish_indicators:
        if indicator in text_lower:
            return "es"
    return "en"

def detect_intent(text: str) -> Dict[str, Any]:
    text_lower = text.lower()
    
    intent = {
        "type": "general",
        "is_emergency": False,
        "wants_appointment": False,
        "needs_pricing": False
    }
    
    emergency_keywords = ['emergency', 'urgent', 'leak', 'flooding', 'gas smell', 'no heat', 'no ac', 'broken']
    appointment_keywords = ['appointment', 'schedule', 'book', 'available', 'come out', 'visit']
    pricing_keywords = ['cost', 'price', 'how much', 'charge', 'rate', 'quote']
    
    for keyword in emergency_keywords:
        if keyword in text_lower:
            intent["is_emergency"] = True
            intent["type"] = "emergency"
            break
    
    for keyword in appointment_keywords:
        if keyword in text_lower:
            intent["wants_appointment"] = True
            if intent["type"] == "general":
                intent["type"] = "appointment"
            break
    
    for keyword in pricing_keywords:
        if keyword in text_lower:
            intent["needs_pricing"] = True
            if intent["type"] == "general":
                intent["type"] = "pricing"
            break
    
    return intent

def analyze_sentiment(text: str) -> str:
    positive_words = ['thank', 'great', 'excellent', 'good', 'happy', 'pleased', 'wonderful']
    negative_words = ['angry', 'frustrated', 'upset', 'terrible', 'awful', 'bad', 'disappointed']
    
    text_lower = text.lower()
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    
    if positive_count > negative_count:
        return "positive"
    elif negative_count > positive_count:
        return "negative"
    return "neutral"
