# Cortana AI Voice System

## Overview
AI-driven voice automation SaaS platform for home-services businesses built by **Doxen Strategy Group**.

### Features
- **Real-time AI Call Handling**: Twilio voice webhooks with OpenAI-powered conversations
- **Live Transcript Streaming**: Server-Sent Events (SSE) for real-time dashboard updates
- **Appointment Booking**: Google Calendar integration
- **Technician Dispatch**: SMS-based dispatch via Twilio
- **Knowledgebase**: Vector search using Pinecone for context-aware AI responses
- **Multi-language Support**: English/Spanish with automatic detection
- **Glassmorphic UI**: Modern frosted glass dashboard design

## Project Architecture

### Backend (FastAPI - Python)
```
/app
  /core
    ai_engine.py       - OpenAI conversation logic
    call_manager.py    - Call flow and transcript management
    cortana_realtime.py - OpenAI Realtime API WebSocket handler
    vector_search.py   - Pinecone knowledge retrieval
    calendar.py        - Google Calendar integration
    dispatcher.py      - Twilio SMS dispatch
    personality.py     - AI personality management
    routing.py         - After-hours and overflow logic
    voicemail.py       - Voicemail summarization
    fallback.py        - Error handling and fallbacks
  /routers
    twilio_router.py   - Voice webhooks
    api_router.py      - Business and technician APIs
    knowledgebase_router.py - KB CRUD operations
    appointments.py    - Booking endpoints
    billing.py         - Stripe webhooks
    stream_router.py   - SSE transcript streaming
  /database
    models.py          - SQLAlchemy models
    session.py         - Database connection
  main.py              - FastAPI application
```

### Frontend (Next.js)
```
/frontend
  /pages
    index.js           - Dashboard
    calls.js           - Live call monitoring
    knowledgebase.js   - KB editor
    personality.js     - AI personality config
    technicians.js     - Team management
    settings.js        - Business settings
  /components
    Sidebar.jsx        - Navigation
    GlassCard.jsx      - Glassmorphic cards
    GlassButton.jsx    - Styled buttons
    TranscriptViewer.jsx - Real-time transcripts
    Layout.jsx         - Page layout
```

### Database Models
- **Business**: Company profiles, settings, AI personality
- **Technician**: Team members with skills and availability
- **CallLog**: Call history, transcripts, sentiment, customer_name, customer_phone, customer_email, customer_address, service_requested
- **KnowledgebaseDocument**: AI knowledge base content
- **ActiveCall**: Real-time call tracking

## Environment Variables Required

### Required for Full Functionality
- `OPENAI_API_KEY` - OpenAI API access (for Realtime API)
- `TWILIO_ACCOUNT_SID` - Twilio account
- `TWILIO_AUTH_TOKEN` - Twilio auth
- `TWILIO_PHONE_NUMBER` - Twilio phone number
- `PINECONE_API_KEY` - Pinecone vector database
- `STRIPE_SECRET_KEY` - Stripe billing
- `STRIPE_WEBHOOK_SECRET` - Stripe webhook verification

### Google Calendar (OAuth via Replit Connector)
Google Calendar is now connected via Replit's built-in OAuth connector - no manual credentials needed.

### Auto-configured
- `DATABASE_URL` - PostgreSQL connection (auto-configured by Replit)

## Running the Application

### Development
The application runs with:
- Backend: FastAPI on port 8000
- Frontend: Next.js on port 5000 (main webview)

### Twilio Webhook Configuration
Set your Twilio webhook URLs to:
- Voice: `https://your-repl.replit.dev/twilio/voice`
- Status: `https://your-repl.replit.dev/twilio/status`
- SMS: `https://your-repl.replit.dev/twilio/sms`

### OpenAI Realtime Voice (Recommended)
For real-time voice streaming with OpenAI's Realtime API:

1. In Twilio Console, set your phone number's "A call comes in" webhook to:
   - **URL**: `https://doxen-ai-voice--doxenstrategy.replit.app/twilio/stream`
   - **Method**: HTTP POST

2. The `/twilio/stream` endpoint returns TwiML that instructs Twilio to open a WebSocket to `/twilio/realtime`

3. Enable Media Streams in Twilio Voice settings with:
   - WebSockets enabled
   - Bidirectional audio
   - Mono audio, G.711 μ-law encoding (mulaw)

## User Preferences
- Glassmorphic UI with frosted glass effects
- Neon accent colors (blue, purple, teal)
- Real-time updates via SSE
- Mobile-responsive design

## Recent Changes
- Initial project setup (December 2025)
- Complete backend with all core modules
- Next.js frontend with glassmorphic dashboard
- SSE transcript streaming
- PostgreSQL database models
- Added OpenAI Realtime API WebSocket handler (December 12, 2025)
- Added /twilio/realtime WebSocket endpoint for live voice streaming
- **Phase 7 Implementation (December 13, 2025)**:
  - Google Calendar integration using Replit's connector (OAuth)
  - Customer data extraction (name, phone, email, address) from speech using regex + AI
  - Intent detection for booking, emergency, pricing, and other intents
  - Automatic appointment booking during voice calls
  - SMS confirmations to customers after booking
  - Technician matching and dispatch via SMS
  - Live transcript streaming via SSE to dashboard
  - Database schema updated with customer data fields in CallLog

## Phase 7 Features

### Customer Data Extraction
The system automatically extracts customer information during calls:
- Name, phone, email, address using regex patterns
- AI-powered extraction for complex cases using GPT-4o-mini
- Data collected throughout the call and finalized at end

### Intent Detection
Real-time intent detection during calls:
- `BOOK_APPOINTMENT` - Customer wants to schedule service
- `EMERGENCY` - Urgent service needed (flooding, gas leak, etc.)
- `PRICING_INQUIRY` - Questions about cost
- `CHECK_AVAILABILITY` - Checking open slots
- `CONFIRMATION/DECLINE` - Response to offers

### Appointment Booking Flow
1. Customer expresses booking intent
2. System fetches available slots from Google Calendar
3. AI offers time slots to customer
4. Customer confirms - booking created in Calendar
5. SMS confirmation sent to customer
6. Technician dispatched via SMS

### New Core Modules
- `data_extractor.py` - Customer data extraction using regex + AI
- `intent_detector.py` - Customer intent classification
- `email_service.py` - Email sending (requires SENDGRID_API_KEY secret)
- `technician_matcher.py` - Smart technician matching with skills scoring

### Live Call Actions API
New endpoints for manual intervention:
- `/api/call-actions/force-assign` - Force assign technician
- `/api/call-actions/cancel-job` - Cancel a job
- `/api/call-actions/override-decision` - Override AI decisions
- `/api/call-actions/auto-assign/{call_id}` - Auto-assign technician

### New Appointment Endpoints
- `/api/appointments/create` - Create appointment
- `/api/appointments/checkAvailability` - Check available slots
- `/api/appointments/customer/update/{call_id}` - Update customer info
- `/api/appointments/calls/store` - Store call logs
- `/api/appointments/technician/assign` - Assign technician
- `/api/appointments/technician/match/{business_id}` - Match technician by skills
