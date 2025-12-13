import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional

async def get_google_calendar_client():
    """Get authenticated Google Calendar client using Replit's connection."""
    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        
        hostname = os.environ.get('REPLIT_CONNECTORS_HOSTNAME')
        repl_identity = os.environ.get('REPL_IDENTITY')
        web_repl_renewal = os.environ.get('WEB_REPL_RENEWAL')
        
        if repl_identity:
            x_replit_token = f'repl {repl_identity}'
        elif web_repl_renewal:
            x_replit_token = f'depl {web_repl_renewal}'
        else:
            return None
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f'https://{hostname}/api/v2/connection?include_secrets=true&connector_names=google-calendar',
                headers={
                    'Accept': 'application/json',
                    'X_REPLIT_TOKEN': x_replit_token
                }
            ) as response:
                data = await response.json()
                connection = data.get('items', [{}])[0]
                
        settings = connection.get('settings', {})
        access_token = settings.get('access_token') or settings.get('oauth', {}).get('credentials', {}).get('access_token')
        
        if not access_token:
            return None
        
        credentials = Credentials(token=access_token)
        service = build('calendar', 'v3', credentials=credentials)
        return service
    except Exception as e:
        print(f"Google Calendar connection error: {e}")
        return None


class CalendarService:
    def __init__(self):
        self.service = None
    
    async def ensure_connected(self):
        """Ensure we have a fresh Google Calendar connection."""
        self.service = await get_google_calendar_client()
        return self.service is not None
    
    async def get_availability(
        self, 
        calendar_id: str = "primary",
        days_ahead: int = 7,
        slot_duration_minutes: int = 60
    ) -> List[Dict]:
        await self.ensure_connected()
        
        if not self.service:
            return self._get_mock_availability(days_ahead, slot_duration_minutes)
        
        try:
            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            busy_times = []
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                busy_times.append((start, end))
            
            return self._calculate_free_slots(now, days_ahead, slot_duration_minutes, busy_times)
        except Exception as e:
            print(f"Calendar availability error: {e}")
            return self._get_mock_availability(days_ahead, slot_duration_minutes)
    
    def _get_mock_availability(self, days_ahead: int, slot_duration: int) -> List[Dict]:
        slots = []
        now = datetime.now()
        
        for day in range(1, min(days_ahead + 1, 8)):
            date = now + timedelta(days=day)
            if date.weekday() < 5:
                for hour in [9, 10, 11, 14, 15, 16]:
                    slot_time = date.replace(hour=hour, minute=0, second=0, microsecond=0)
                    slots.append({
                        "start": slot_time.isoformat(),
                        "end": (slot_time + timedelta(minutes=slot_duration)).isoformat(),
                        "display": slot_time.strftime("%A, %B %d at %I:%M %p")
                    })
        
        return slots[:10]
    
    def _calculate_free_slots(
        self, 
        start_date: datetime, 
        days: int, 
        duration: int, 
        busy_times: list
    ) -> List[Dict]:
        slots = []
        business_hours = [(9, 17)]
        
        for day in range(1, days + 1):
            current_date = start_date + timedelta(days=day)
            if current_date.weekday() >= 5:
                continue
            
            for start_hour, end_hour in business_hours:
                current_time = current_date.replace(hour=start_hour, minute=0, second=0, microsecond=0)
                end_time = current_date.replace(hour=end_hour, minute=0, second=0, microsecond=0)
                
                while current_time + timedelta(minutes=duration) <= end_time:
                    slot_end = current_time + timedelta(minutes=duration)
                    is_free = True
                    
                    for busy_start, busy_end in busy_times:
                        if isinstance(busy_start, str):
                            busy_start = datetime.fromisoformat(busy_start.replace('Z', '+00:00'))
                        if isinstance(busy_end, str):
                            busy_end = datetime.fromisoformat(busy_end.replace('Z', '+00:00'))
                        
                        if not (slot_end <= busy_start or current_time >= busy_end):
                            is_free = False
                            break
                    
                    if is_free:
                        slots.append({
                            "start": current_time.isoformat(),
                            "end": slot_end.isoformat(),
                            "display": current_time.strftime("%A, %B %d at %I:%M %p")
                        })
                    
                    current_time += timedelta(minutes=30)
        
        return slots[:20]
    
    async def book_appointment(
        self,
        calendar_id: str = "primary",
        summary: str = "Service Appointment",
        description: str = "",
        start_time: str = "",
        duration_minutes: int = 60,
        attendee_email: str = None,
        customer_info: Dict = None
    ) -> Optional[Dict]:
        await self.ensure_connected()
        
        if not self.service:
            return {
                "success": True,
                "event_id": "mock_" + datetime.now().strftime("%Y%m%d%H%M%S"),
                "start": start_time,
                "summary": summary,
                "mock": True
            }
        
        try:
            start_dt = datetime.fromisoformat(start_time)
            end_dt = start_dt + timedelta(minutes=duration_minutes)
            
            full_description = description
            if customer_info:
                full_description += f"\n\nCustomer Details:\n"
                full_description += f"Name: {customer_info.get('name', 'N/A')}\n"
                full_description += f"Phone: {customer_info.get('phone', 'N/A')}\n"
                full_description += f"Address: {customer_info.get('address', 'N/A')}\n"
                full_description += f"Email: {customer_info.get('email', 'N/A')}\n"
            
            event = {
                'summary': summary,
                'description': full_description.strip(),
                'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'America/New_York'},
                'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'America/New_York'},
            }
            
            if attendee_email:
                event['attendees'] = [{'email': attendee_email}]
            
            created_event = self.service.events().insert(
                calendarId=calendar_id,
                body=event
            ).execute()
            
            return {
                "success": True,
                "event_id": created_event['id'],
                "start": start_time,
                "summary": summary,
                "link": created_event.get('htmlLink')
            }
        except Exception as e:
            print(f"Booking error: {e}")
            return None
    
    async def get_next_available_slot(self, service_type: str = "service") -> Optional[Dict]:
        """Get the next available appointment slot."""
        slots = await self.get_availability(days_ahead=7, slot_duration_minutes=60)
        if slots:
            return slots[0]
        return None

calendar_service = CalendarService()
