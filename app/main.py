import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .database.session import init_db, SessionLocal
from .routers import twilio_router, api_router, knowledgebase_router, appointments, billing, stream_router

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

app.include_router(twilio_router.router)
app.include_router(api_router.router)
app.include_router(knowledgebase_router.router)
app.include_router(appointments.router)
app.include_router(billing.router)
app.include_router(stream_router.router)

@app.on_event("startup")
async def startup_event():
    init_db()
    print("Database initialized")
    
    if SessionLocal:
        from .database.models import Business
        db = SessionLocal()
        try:
            if not db.query(Business).first():
                print("No businesses found. Run 'python seed_data.py' to seed demo data.")
        finally:
            db.close()

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
        "google_calendar": bool(os.environ.get("GOOGLE_CALENDAR_CREDENTIALS")),
        "stripe": bool(os.environ.get("STRIPE_SECRET_KEY"))
    }

if os.path.exists("frontend/out"):
    app.mount("/static", StaticFiles(directory="frontend/out"), name="static")
    
    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        file_path = f"frontend/out/{path}"
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        
        index_path = "frontend/out/index.html"
        if os.path.exists(index_path):
            return FileResponse(index_path)
        
        return {"error": "Frontend not built"}
