import os
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from .database.session import init_db, SessionLocal
from .routers import twilio_router, api_router, knowledgebase_router, appointments, billing, stream_router, call_actions, business_router
from .routers import analytics_router, quotes_router, outbound_router, subscription_router

app = FastAPI(
    title="Cortana AI Voice System",
    description="AI-driven voice automation SaaS for home-services businesses",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root health check - responds immediately."""
    return JSONResponse({"status": "ok", "message": "Cortana AI Voice System", "version": "1.0.0"})

@app.get("/health")
async def health_check():
    """Health check endpoint for deployment monitoring."""
    return JSONResponse({"status": "healthy"})

app.include_router(twilio_router.router)
app.include_router(api_router.router)
app.include_router(knowledgebase_router.router)
app.include_router(appointments.router)
app.include_router(billing.router)
app.include_router(stream_router.router)
app.include_router(call_actions.router)
app.include_router(business_router.router)
app.include_router(analytics_router.router)
app.include_router(quotes_router.router)
app.include_router(outbound_router.router)
app.include_router(subscription_router.router)

db_initialized = False

async def init_database_background():
    """Initialize database in background without blocking startup."""
    global db_initialized
    try:
        init_db()
        print("Database initialized")
        db_initialized = True
        
        if SessionLocal:
            from .database.models import Business
            db = SessionLocal()
            try:
                if not db.query(Business).first():
                    print("No businesses found. Run 'python seed_data.py' to seed demo data.")
            finally:
                db.close()
    except Exception as e:
        print(f"Database initialization error: {e}")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(init_database_background())

@app.get("/api/info")
async def get_info():
    return {
        "name": "Cortana AI Voice System",
        "version": "1.0.0",
        "company": "Doxen Strategy Group",
        "status": "operational"
    }

@app.get("/api/integrations/status")
async def get_integration_status():
    return {
        "database": bool(os.environ.get("DATABASE_URL")),
        "openai": bool(os.environ.get("OPENAI_API_KEY")),
        "twilio": bool(os.environ.get("TWILIO_ACCOUNT_SID")),
        "pinecone": bool(os.environ.get("PINECONE_API_KEY")),
        "google_calendar": True,
        "stripe": bool(os.environ.get("STRIPE_SECRET_KEY")),
        "sendgrid": bool(os.environ.get("SENDGRID_API_KEY"))
    }

FRONTEND_DIR = "frontend/out"

@app.get("/app")
async def serve_app():
    """Serve the frontend application."""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"error": "Frontend not built"}

if os.path.exists(FRONTEND_DIR):
    app.mount("/_next", StaticFiles(directory=os.path.join(FRONTEND_DIR, "_next")), name="next_static")

@app.get("/{path:path}")
async def serve_frontend(path: str):
    if path.startswith("api/") or path.startswith("twilio/") or path.startswith("billing/"):
        return {"error": "Not found"}
    
    file_path = os.path.join(FRONTEND_DIR, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    
    html_path = os.path.join(FRONTEND_DIR, path, "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path, media_type="text/html")
    
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    
    return {"error": "Frontend not built. Run: cd frontend && npm run build"}
