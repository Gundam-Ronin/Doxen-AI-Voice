from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

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
async def health_root():
    """Instant health check - zero imports, zero dependencies."""
    return JSONResponse({"status": "ok"}, status_code=200)

@app.get("/health")
async def health_check():
    """Health check endpoint - instant response."""
    return JSONResponse({"status": "ok"}, status_code=200)

@app.middleware("http")
async def load_routers_middleware(request: Request, call_next):
    """Load routers only on non-health-check requests."""
    if request.url.path not in ["/", "/health"]:
        from .router_loader import load_routers
        load_routers(app)
    return await call_next(request)

@app.on_event("startup")
async def startup_event():
    """Minimal startup - just log ready status."""
    print("Application started - ready for health checks")
