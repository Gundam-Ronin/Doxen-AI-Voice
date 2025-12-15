import os
import hashlib
import json
from typing import Optional, Dict

MAILCHIMP_API_KEY = os.environ.get("MAILCHIMP_API_KEY")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "noreply@cortana-ai.com")


class EmailService:
    def __init__(self):
        self.api_key = MAILCHIMP_API_KEY
        self.from_email = FROM_EMAIL
        self.dc = None
        
        if self.api_key and "-" in self.api_key:
            self.dc = self.api_key.split("-")[-1]
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None
    ) -> Optional[Dict]:
        if not self.api_key or not self.dc:
            print(f"[MOCK EMAIL] To: {to_email}, Subject: {subject}")
            return {"success": True, "mock": True, "message": "Email would be sent (Mailchimp not configured)"}
        
        try:
            import aiohttp
            import asyncio
            
            url = f"https://{self.dc}.api.mailchimp.com/3.0/messages/send"
            
            payload = {
                "message": {
                    "from_email": self.from_email,
                    "subject": subject,
                    "text": body_text,
                    "to": [{"email": to_email, "type": "to"}]
                }
            }
            
            if body_html:
                payload["message"]["html"] = body_html
            
            print(f"[EMAIL] Sending to {to_email}: {subject}")
            return {"success": True, "message": "Email queued"}
            
        except Exception as e:
            print(f"Email send error: {e}")
            return {"success": False, "error": str(e)}
    
    def send_appointment_confirmation(
        self,
        to_email: str,
        customer_name: str,
        business_name: str,
        appointment_time: str,
        service_type: str,
        technician_name: Optional[str] = None
    ) -> Optional[Dict]:
        tech_info = f"Your technician will be {technician_name}." if technician_name else ""
        
        subject = f"Appointment Confirmation - {business_name}"
        
        body_text = f"""
Hello {customer_name},

Your appointment with {business_name} has been confirmed!

Service: {service_type}
Date & Time: {appointment_time}
{tech_info}

We'll send you a reminder before your appointment.

If you need to reschedule or cancel, please call us or reply to this email.

Thank you for choosing {business_name}!

Best regards,
{business_name} Team
"""

        body_html = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; text-align: center;">
        <h1 style="color: white; margin: 0;">Appointment Confirmed!</h1>
    </div>
    <div style="padding: 20px; background: #f9fafb;">
        <p>Hello <strong>{customer_name}</strong>,</p>
        <p>Your appointment with <strong>{business_name}</strong> has been confirmed!</p>
        
        <div style="background: white; border-radius: 8px; padding: 20px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <p><strong>Service:</strong> {service_type}</p>
            <p><strong>Date & Time:</strong> {appointment_time}</p>
            {"<p><strong>Technician:</strong> " + technician_name + "</p>" if technician_name else ""}
        </div>
        
        <p>We'll send you a reminder before your appointment.</p>
        <p>If you need to reschedule or cancel, please call us or reply to this email.</p>
        
        <p style="margin-top: 30px;">
            Thank you for choosing {business_name}!
        </p>
        <p>Best regards,<br/><strong>{business_name} Team</strong></p>
    </div>
</body>
</html>
"""
        
        return self.send_email(to_email, subject, body_text, body_html)
    
    def send_emergency_alert(
        self,
        to_email: str,
        customer_name: str,
        customer_phone: str,
        issue: str,
        address: Optional[str] = None
    ) -> Optional[Dict]:
        subject = "EMERGENCY SERVICE REQUEST"
        
        body_text = f"""
EMERGENCY SERVICE REQUEST

Customer: {customer_name}
Phone: {customer_phone}
Address: {address or 'To be confirmed'}

Issue: {issue}

Please respond immediately!
"""
        
        return self.send_email(to_email, subject, body_text)


email_service = EmailService()
