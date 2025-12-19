import os

_routers_loaded = False

def load_routers(app):
    """Load all routers - called only on first real API request."""
    global _routers_loaded
    if _routers_loaded:
        return
    _routers_loaded = True
    
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    
    from .database.session import init_db, get_session_local
    from .routers import twilio_router, api_router, knowledgebase_router, appointments, billing, stream_router, call_actions, business_router
    from .routers import analytics_router, quotes_router, outbound_router, subscription_router
    
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
    
    try:
        init_db()
        print("Database initialized")
    except Exception as e:
        print(f"Database initialization error: {e}")
    
    print("All routers loaded successfully")
