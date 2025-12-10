import os
from typing import Optional, Dict, List
from twilio.rest import Client

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

class Dispatcher:
    def __init__(self):
        self.client = None
        if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
            try:
                self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            except Exception as e:
                print(f"Twilio initialization error: {e}")
    
    def send_sms(self, to_number: str, message: str) -> Optional[Dict]:
        if not self.client:
            print(f"[MOCK SMS] To: {to_number}, Message: {message}")
            return {"success": True, "sid": "mock_sms_sid", "mock": True}
        
        try:
            sms = self.client.messages.create(
                body=message,
                from_=TWILIO_PHONE_NUMBER,
                to=to_number
            )
            return {"success": True, "sid": sms.sid}
        except Exception as e:
            print(f"SMS error: {e}")
            return {"success": False, "error": str(e)}
    
    def dispatch_technician(
        self,
        technician_name: str,
        technician_phone: str,
        customer_info: Dict,
        appointment_time: str,
        service_type: str,
        is_emergency: bool = False
    ) -> Optional[Dict]:
        priority = "🚨 EMERGENCY" if is_emergency else "📅 Scheduled"
        
        message = f"""{priority} Service Request

Customer: {customer_info.get('name', 'N/A')}
Phone: {customer_info.get('phone', 'N/A')}
Address: {customer_info.get('address', 'To be confirmed')}

Service: {service_type}
Time: {appointment_time}

Please confirm by replying YES or call dispatch if unavailable."""

        result = self.send_sms(technician_phone, message)
        
        if result and result.get("success"):
            return {
                "success": True,
                "technician": technician_name,
                "message_sid": result.get("sid"),
                "is_emergency": is_emergency
            }
        return None
    
    def send_customer_confirmation(
        self,
        customer_phone: str,
        business_name: str,
        appointment_time: str,
        technician_name: str = None
    ) -> Optional[Dict]:
        tech_info = f"Your technician will be {technician_name}." if technician_name else ""
        
        message = f"""Your appointment with {business_name} is confirmed!

📅 {appointment_time}
{tech_info}

We'll send a reminder before the appointment. Reply HELP for assistance or CANCEL to reschedule.

Thank you for choosing {business_name}!"""

        return self.send_sms(customer_phone, message)
    
    def notify_emergency(
        self,
        technicians: List[Dict],
        emergency_details: Dict
    ) -> List[Dict]:
        results = []
        
        message = f"""🚨 EMERGENCY DISPATCH 🚨

Customer: {emergency_details.get('customer_phone', 'N/A')}
Issue: {emergency_details.get('issue', 'Emergency service needed')}
Location: {emergency_details.get('address', 'To be confirmed')}

First available technician please respond ASAP!
Reply ACCEPT to take this job."""

        for tech in technicians:
            if tech.get('is_available', True):
                result = self.send_sms(tech['phone'], message)
                results.append({
                    "technician": tech['name'],
                    "phone": tech['phone'],
                    "notified": result.get("success", False) if result else False
                })
        
        return results

dispatcher = Dispatcher()
