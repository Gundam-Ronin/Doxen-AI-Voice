import os
from typing import Dict, Any, Optional

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = None

def get_openai_client():
    global client
    if client is None and OPENAI_API_KEY:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
    return client

class VoicemailProcessor:
    def __init__(self):
        pass
    
    async def transcribe_voicemail(self, audio_url: str) -> Optional[str]:
        return None
    
    def summarize_voicemail(self, transcript: str) -> Dict[str, Any]:
        if not transcript:
            return {
                "summary": "No transcript available",
                "caller_intent": "unknown",
                "urgency": "normal",
                "callback_requested": False,
                "key_points": []
            }
        
        openai_client = get_openai_client()
        if not openai_client:
            return {
                "summary": transcript[:200] + "..." if len(transcript) > 200 else transcript,
                "caller_intent": "unknown",
                "urgency": "normal",
                "callback_requested": True,
                "key_points": []
            }
        
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """Analyze this voicemail transcript and provide a structured summary.
Return a JSON object with:
- summary: Brief 1-2 sentence summary
- caller_intent: What does the caller want? (appointment, pricing, complaint, inquiry, emergency, other)
- urgency: (low, normal, high, emergency)
- callback_requested: true/false
- key_points: Array of important details mentioned
- phone_number: If mentioned in the message
- name: If the caller states their name"""
                    },
                    {
                        "role": "user",
                        "content": f"Voicemail transcript:\n{transcript}"
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=500
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            print(f"Voicemail summarization error: {e}")
            return {
                "summary": transcript[:200] + "..." if len(transcript) > 200 else transcript,
                "caller_intent": "unknown",
                "urgency": "normal",
                "callback_requested": True,
                "key_points": []
            }
    
    def create_follow_up_task(
        self,
        voicemail_summary: Dict[str, Any],
        business_id: int
    ) -> Dict[str, Any]:
        priority = "high" if voicemail_summary.get("urgency") in ["high", "emergency"] else "normal"
        
        task = {
            "business_id": business_id,
            "type": "voicemail_followup",
            "priority": priority,
            "summary": voicemail_summary.get("summary", ""),
            "caller_intent": voicemail_summary.get("caller_intent", "unknown"),
            "callback_number": voicemail_summary.get("phone_number"),
            "caller_name": voicemail_summary.get("name"),
            "key_points": voicemail_summary.get("key_points", []),
            "status": "pending"
        }
        
        return task

voicemail_processor = VoicemailProcessor()
