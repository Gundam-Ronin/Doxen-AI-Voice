import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

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

FRONTEND_DIR = "frontend/out"

@app.get("/")
async def root():
    """Serve frontend homepage."""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return JSONResponse({"status": "ok", "message": "Frontend not built"}, status_code=200)

@app.get("/health")
async def health():
    """Health check endpoint for deployments."""
    return JSONResponse({"status": "healthy"}, status_code=200)

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

try:
    from .database.session import init_db
    from .routers import twilio_router
    from .routers import api_router
    from .routers import knowledgebase_router
    from .routers import appointments
    from .routers import billing
    from .routers import stream_router
    from .routers import call_actions
    from .routers import business_router
    from .routers import analytics_router
    from .routers import quotes_router
    from .routers import outbound_router
    from .routers import subscription_router

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
    
    ROUTERS_LOADED = True
except Exception as e:
    print(f"Router import error (non-fatal): {e}")
    init_db = None
    ROUTERS_LOADED = False

@app.get("/app")
async def serve_app():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"error": "Frontend not built"}

if os.path.exists(FRONTEND_DIR):
    try:
        app.mount("/_next", StaticFiles(directory=os.path.join(FRONTEND_DIR, "_next")), name="next_static")
    except Exception:
        pass

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
    
    return {"error": "Frontend not built"}

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup - non-blocking."""
    if init_db:
        try:
            if init_db():
                print("Database initialized successfully")
            else:
                print("Database initialization skipped or failed - app continues")
        except Exception as e:
            print(f"Database init error (non-fatal): {e}")
    
    if ROUTERS_LOADED:
        print("Application ready - all routes loaded")
    else:
        print("Application ready - running in minimal mode (routers failed to load)")
