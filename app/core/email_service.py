import os
from typing import Optional, Dict

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "noreply@cortana-ai.com")


class EmailService:
    def __init__(self):
        self.api_key = SENDGRID_API_KEY
        self.from_email = FROM_EMAIL
        self.client = None
        
        if self.api_key:
            try:
                import sendgrid
                self.client = sendgrid.SendGridAPIClient(api_key=self.api_key)
            except ImportError:
                print("SendGrid not installed. Email functionality disabled.")
            except Exception as e:
                print(f"SendGrid initialization error: {e}")
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None
    ) -> Optional[Dict]:
        if not self.client:
            print(f"[MOCK EMAIL] To: {to_email}, Subject: {subject}")
            return {"success": True, "mock": True, "message": "Email would be sent"}
        
        try:
            from sendgrid.helpers.mail import Mail, Email, To, Content
            
            message = Mail(
                from_email=Email(self.from_email),
                to_emails=To(to_email),
                subject=subject,
                plain_text_content=Content("text/plain", body_text)
            )
            
            if body_html:
                message.add_content(Content("text/html", body_html))
            
            response = self.client.send(message)
            
            return {
                "success": response.status_code in [200, 201, 202],
                "status_code": response.status_code
            }
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
