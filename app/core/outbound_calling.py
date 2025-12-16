"""
Phase 8.1 - Outbound AI Calling Engine
Cortana makes outbound calls for follow-ups, reminders, and reviews.
"""

import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")


class OutboundCallType(Enum):
    MISSED_CALL_FOLLOWUP = "missed_call_followup"
    QUOTE_REMINDER = "quote_reminder"
    TECHNICIAN_EN_ROUTE = "technician_en_route"
    REVIEW_REQUEST = "review_request"
    UNCONVERTED_LEAD = "unconverted_lead"
    DEAD_LEAD_REACTIVATION = "dead_lead_reactivation"
    CONTRACT_RENEWAL = "contract_renewal"
    PAYMENT_REMINDER = "payment_reminder"
    APPOINTMENT_REMINDER = "appointment_reminder"
    SERVICE_FOLLOW_UP = "service_follow_up"


@dataclass
class OutboundCallRequest:
    call_type: OutboundCallType
    customer_phone: str
    customer_name: str
    business_id: int
    business_name: str
    context: Dict[str, Any] = field(default_factory=dict)
    scheduled_time: Optional[datetime] = None
    priority: int = 5
    max_attempts: int = 3


@dataclass
class OutboundCallResult:
    success: bool
    call_sid: Optional[str] = None
    status: str = ""
    message: str = ""
    duration_seconds: int = 0
    outcome: Optional[str] = None
    follow_up_required: bool = False


class OutboundCallingEngine:
    """Manages outbound AI calls for various customer touchpoints."""
    
    def __init__(self):
        self.call_queue: List[OutboundCallRequest] = []
        self.call_history: List[Dict] = []
        self.client = None
        
        self.scripts = {
            OutboundCallType.MISSED_CALL_FOLLOWUP: self._script_missed_call,
            OutboundCallType.QUOTE_REMINDER: self._script_quote_reminder,
            OutboundCallType.TECHNICIAN_EN_ROUTE: self._script_tech_en_route,
            OutboundCallType.REVIEW_REQUEST: self._script_review_request,
            OutboundCallType.UNCONVERTED_LEAD: self._script_unconverted_lead,
            OutboundCallType.DEAD_LEAD_REACTIVATION: self._script_dead_lead,
            OutboundCallType.CONTRACT_RENEWAL: self._script_contract_renewal,
            OutboundCallType.PAYMENT_REMINDER: self._script_payment_reminder,
            OutboundCallType.APPOINTMENT_REMINDER: self._script_appointment_reminder,
            OutboundCallType.SERVICE_FOLLOW_UP: self._script_service_follow_up,
        }
        
        self.optimal_call_hours = {
            "start": 9,
            "end": 20,
            "best_morning": (10, 11),
            "best_afternoon": (14, 16),
            "best_evening": (18, 19)
        }
    
    def _get_client(self):
        if self.client is None and TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
            try:
                from twilio.rest import Client
                self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            except Exception as e:
                print(f"Twilio client error: {e}")
        return self.client
    
    def queue_call(self, request: OutboundCallRequest) -> bool:
        """Add a call to the queue."""
        if not request.scheduled_time:
            request.scheduled_time = self._get_optimal_call_time()
        
        self.call_queue.append(request)
        self.call_queue.sort(key=lambda x: (x.scheduled_time, -x.priority))
        
        return True
    
    def _get_optimal_call_time(self) -> datetime:
        """Calculate the optimal time to make the call."""
        now = datetime.now()
        current_hour = now.hour
        
        if self.optimal_call_hours["start"] <= current_hour < self.optimal_call_hours["end"]:
            return now + timedelta(minutes=5)
        
        if current_hour < self.optimal_call_hours["start"]:
            return now.replace(hour=self.optimal_call_hours["start"], minute=0)
        else:
            tomorrow = now + timedelta(days=1)
            return tomorrow.replace(hour=self.optimal_call_hours["start"], minute=0)
    
    def initiate_call(self, request: OutboundCallRequest, webhook_base_url: str) -> OutboundCallResult:
        """Initiate an outbound call."""
        client = self._get_client()
        if not client:
            return OutboundCallResult(
                success=False,
                status="error",
                message="Twilio client not configured"
            )
        
        try:
            script_generator = self.scripts.get(request.call_type)
            if not script_generator:
                return OutboundCallResult(
                    success=False,
                    status="error",
                    message=f"No script for call type: {request.call_type}"
                )
            
            twiml = script_generator(request)
            
            callback_url = f"{webhook_base_url}/twilio/outbound-status"
            
            call = client.calls.create(
                to=request.customer_phone,
                from_=TWILIO_PHONE_NUMBER,
                twiml=twiml,
                status_callback=callback_url,
                status_callback_event=["initiated", "answered", "completed"],
                machine_detection="Enable",
                machine_detection_timeout=5
            )
            
            self.call_history.append({
                "call_sid": call.sid,
                "request": request,
                "initiated_at": datetime.now(),
                "status": "initiated"
            })
            
            return OutboundCallResult(
                success=True,
                call_sid=call.sid,
                status="initiated",
                message=f"Call initiated to {request.customer_phone}"
            )
            
        except Exception as e:
            return OutboundCallResult(
                success=False,
                status="error",
                message=str(e)
            )
    
    def _script_missed_call(self, request: OutboundCallRequest) -> str:
        """Generate TwiML for missed call follow-up."""
        name = request.customer_name or "there"
        business = request.business_name
        
        return f"""
        <Response>
            <Say voice="Polly.Joanna">
                Hi {name}, this is Cortana calling from {business}. 
                I noticed we missed your call earlier, and I wanted to make sure we got back to you.
                How can I help you today?
            </Say>
            <Gather input="speech" timeout="5" action="/twilio/outbound-response">
                <Say>I'm listening.</Say>
            </Gather>
            <Say>
                I didn't catch that. If you'd like to schedule a service call, 
                please call us back at your convenience. Thank you!
            </Say>
        </Response>
        """
    
    def _script_quote_reminder(self, request: OutboundCallRequest) -> str:
        """Generate TwiML for quote reminder."""
        name = request.customer_name or "there"
        business = request.business_name
        service = request.context.get("service_type", "the service")
        quote_amount = request.context.get("quote_amount", "")
        
        quote_mention = f" for {quote_amount}" if quote_amount else ""
        
        return f"""
        <Response>
            <Say voice="Polly.Joanna">
                Hi {name}, this is Cortana from {business}. 
                I'm following up on the quote we provided{quote_mention} for {service}.
                I wanted to see if you had any questions or if you're ready to schedule?
            </Say>
            <Gather input="speech" timeout="5" action="/twilio/outbound-response">
                <Say>Would you like to proceed with scheduling?</Say>
            </Gather>
            <Say>
                No problem! Feel free to call us back when you're ready. 
                Have a great day!
            </Say>
        </Response>
        """
    
    def _script_tech_en_route(self, request: OutboundCallRequest) -> str:
        """Generate TwiML for technician en route notification."""
        name = request.customer_name or "there"
        business = request.business_name
        tech_name = request.context.get("technician_name", "your technician")
        eta = request.context.get("eta", "shortly")
        
        return f"""
        <Response>
            <Say voice="Polly.Joanna">
                Hi {name}, this is Cortana from {business}. 
                I'm calling to let you know that {tech_name} is on the way 
                and should arrive {eta}.
                Please make sure someone is available to let them in.
                Is there anything you need before they arrive?
            </Say>
            <Gather input="speech" timeout="3" action="/twilio/outbound-response">
                <Say>I'm listening.</Say>
            </Gather>
            <Say>
                Perfect. We'll see you soon. Thank you!
            </Say>
        </Response>
        """
    
    def _script_review_request(self, request: OutboundCallRequest) -> str:
        """Generate TwiML for review request."""
        name = request.customer_name or "there"
        business = request.business_name
        tech_name = request.context.get("technician_name", "our technician")
        
        return f"""
        <Response>
            <Say voice="Polly.Joanna">
                Hi {name}, this is Cortana from {business}. 
                I hope {tech_name} took great care of you today!
                We'd really appreciate if you could leave us a quick review.
                On a scale of 1 to 5, how would you rate your experience?
            </Say>
            <Gather input="dtmf speech" timeout="5" numDigits="1" action="/twilio/review-response">
                <Say>Please say a number or press 1 through 5.</Say>
            </Gather>
            <Say>
                Thank you for your time! If you'd like to leave a detailed review, 
                we'll send you a text with a link. Have a wonderful day!
            </Say>
        </Response>
        """
    
    def _script_unconverted_lead(self, request: OutboundCallRequest) -> str:
        """Generate TwiML for unconverted lead follow-up."""
        name = request.customer_name or "there"
        business = request.business_name
        days_ago = request.context.get("days_since_contact", "a few days")
        service = request.context.get("service_type", "home services")
        
        return f"""
        <Response>
            <Say voice="Polly.Joanna">
                Hi {name}, this is Cortana from {business}. 
                We spoke {days_ago} ago about {service}, 
                and I wanted to follow up to see if you still needed help.
                Are you still looking for service?
            </Say>
            <Gather input="speech" timeout="5" action="/twilio/outbound-response">
                <Say>Just say yes or no.</Say>
            </Gather>
            <Say>
                I understand. If you ever need us, we're just a phone call away. 
                Thank you and have a great day!
            </Say>
        </Response>
        """
    
    def _script_dead_lead(self, request: OutboundCallRequest) -> str:
        """Generate TwiML for dead lead reactivation."""
        name = request.customer_name or "there"
        business = request.business_name
        
        return f"""
        <Response>
            <Say voice="Polly.Joanna">
                Hi {name}, this is Cortana from {business}. 
                It's been a while since we last connected, and I wanted to reach out 
                to see if there's anything we can help you with.
                We have some great seasonal specials running right now.
                Would you be interested in hearing about them?
            </Say>
            <Gather input="speech" timeout="5" action="/twilio/outbound-response">
                <Say>Just say yes or no.</Say>
            </Gather>
            <Say>
                No problem at all. We'll be here when you need us. Take care!
            </Say>
        </Response>
        """
    
    def _script_contract_renewal(self, request: OutboundCallRequest) -> str:
        """Generate TwiML for contract renewal reminder."""
        name = request.customer_name or "there"
        business = request.business_name
        expiry_date = request.context.get("contract_expiry", "soon")
        discount = request.context.get("renewal_discount", "10%")
        
        return f"""
        <Response>
            <Say voice="Polly.Joanna">
                Hi {name}, this is Cortana from {business}. 
                I'm calling because your service agreement is coming up for renewal {expiry_date}.
                As a valued customer, we'd like to offer you {discount} off 
                if you renew today. Would you like to take advantage of this offer?
            </Say>
            <Gather input="speech" timeout="5" action="/twilio/outbound-response">
                <Say>Would you like to renew?</Say>
            </Gather>
            <Say>
                I understand. I'll send you the details by text so you can review them. 
                Thank you for being a loyal customer!
            </Say>
        </Response>
        """
    
    def _script_payment_reminder(self, request: OutboundCallRequest) -> str:
        """Generate TwiML for payment reminder."""
        name = request.customer_name or "there"
        business = request.business_name
        amount = request.context.get("amount_due", "your balance")
        due_date = request.context.get("due_date", "as soon as possible")
        
        return f"""
        <Response>
            <Say voice="Polly.Joanna">
                Hi {name}, this is a friendly reminder from {business}. 
                You have an outstanding balance of {amount} due {due_date}.
                Would you like to make a payment now, or would you prefer 
                we send you a payment link by text?
            </Say>
            <Gather input="speech" timeout="5" action="/twilio/payment-response">
                <Say>How would you like to proceed?</Say>
            </Gather>
            <Say>
                No problem. We'll send you a payment link by text. 
                If you have any questions, please call us back. Thank you!
            </Say>
        </Response>
        """
    
    def _script_appointment_reminder(self, request: OutboundCallRequest) -> str:
        """Generate TwiML for appointment reminder."""
        name = request.customer_name or "there"
        business = request.business_name
        apt_date = request.context.get("appointment_date", "tomorrow")
        apt_time = request.context.get("appointment_time", "")
        tech_name = request.context.get("technician_name", "your technician")
        
        return f"""
        <Response>
            <Say voice="Polly.Joanna">
                Hi {name}, this is Cortana from {business}. 
                Just a friendly reminder that {tech_name} is scheduled to visit 
                {apt_date} {apt_time}.
                Will you be available at that time?
            </Say>
            <Gather input="speech" timeout="5" action="/twilio/confirm-response">
                <Say>Please confirm with yes, or say reschedule if you need a different time.</Say>
            </Gather>
            <Say>
                We'll keep your appointment as scheduled. 
                See you {apt_date}! Have a great day!
            </Say>
        </Response>
        """
    
    def _script_service_follow_up(self, request: OutboundCallRequest) -> str:
        """Generate TwiML for post-service follow-up."""
        name = request.customer_name or "there"
        business = request.business_name
        service = request.context.get("service_type", "service")
        
        return f"""
        <Response>
            <Say voice="Polly.Joanna">
                Hi {name}, this is Cortana from {business}. 
                I'm just following up on the {service} we completed for you.
                Is everything working well? Are you satisfied with the work?
            </Say>
            <Gather input="speech" timeout="5" action="/twilio/feedback-response">
                <Say>How is everything?</Say>
            </Gather>
            <Say>
                That's wonderful to hear! Thank you for choosing {business}. 
                Please don't hesitate to call if you need anything else!
            </Say>
        </Response>
        """
    
    def get_pending_calls(self) -> List[OutboundCallRequest]:
        """Get calls that are due to be made."""
        now = datetime.now()
        return [
            call for call in self.call_queue
            if call.scheduled_time <= now
        ]
    
    def process_queue(self, webhook_base_url: str) -> List[OutboundCallResult]:
        """Process pending calls in the queue."""
        results = []
        pending = self.get_pending_calls()
        
        for call_request in pending:
            result = self.initiate_call(call_request, webhook_base_url)
            results.append(result)
            
            if result.success:
                self.call_queue.remove(call_request)
        
        return results
    
    def schedule_missed_call_followup(
        self,
        customer_phone: str,
        customer_name: str,
        business_id: int,
        business_name: str,
        delay_minutes: int = 30
    ) -> bool:
        """Schedule a follow-up for a missed call."""
        request = OutboundCallRequest(
            call_type=OutboundCallType.MISSED_CALL_FOLLOWUP,
            customer_phone=customer_phone,
            customer_name=customer_name,
            business_id=business_id,
            business_name=business_name,
            scheduled_time=datetime.now() + timedelta(minutes=delay_minutes),
            priority=8
        )
        return self.queue_call(request)
    
    def schedule_review_request(
        self,
        customer_phone: str,
        customer_name: str,
        business_id: int,
        business_name: str,
        technician_name: str,
        delay_hours: int = 2
    ) -> bool:
        """Schedule a review request call after service completion."""
        request = OutboundCallRequest(
            call_type=OutboundCallType.REVIEW_REQUEST,
            customer_phone=customer_phone,
            customer_name=customer_name,
            business_id=business_id,
            business_name=business_name,
            context={"technician_name": technician_name},
            scheduled_time=datetime.now() + timedelta(hours=delay_hours),
            priority=5
        )
        return self.queue_call(request)


outbound_calling_engine = OutboundCallingEngine()
