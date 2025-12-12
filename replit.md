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
- **CallLog**: Call history, transcripts, sentiment
- **KnowledgebaseDocument**: AI knowledge base content
- **ActiveCall**: Real-time call tracking

## Environment Variables Required

### Required for Full Functionality
- `OPENAI_API_KEY` - OpenAI API access (for Realtime API)
- `TWILIO_ACCOUNT_SID` - Twilio account
- `TWILIO_AUTH_TOKEN` - Twilio auth
- `TWILIO_PHONE_NUMBER` - Twilio phone number
- `PINECONE_API_KEY` - Pinecone vector database
- `GOOGLE_CALENDAR_CREDENTIALS` - Google Calendar JSON credentials
- `STRIPE_SECRET_KEY` - Stripe billing
- `STRIPE_WEBHOOK_SECRET` - Stripe webhook verification

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
1. In Twilio Console, configure your phone number's Voice TwiML:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say>Please hold while we connect you to our AI assistant.</Say>
  <Connect>
    <Stream url="wss://your-repl.replit.app/twilio/realtime" />
  </Connect>
</Response>
```
2. Enable Media Streams in Twilio Voice settings with:
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
