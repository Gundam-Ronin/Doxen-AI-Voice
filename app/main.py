import asyncio
from fastapi import FastAPI
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
async def root():
    """Instant health check - responds immediately."""
    return JSONResponse({"status": "ok"}, status_code=200)

@app.get("/health")
async def health():
    """Health check endpoint - instant response."""
    return JSONResponse({"status": "healthy"}, status_code=200)

async def load_everything_async():
    """Load routers after health check has time to respond."""
    await asyncio.sleep(0.5)
    
    from .router_loader import load_routers
    load_routers(app)
    
    print("Routers + DB fully loaded and ready for Twilio.")

@app.on_event("startup")
async def startup_event():
    """Start router loading in background after health check window."""
    asyncio.create_task(load_everything_async())
    print("Application started - ready for health checks")
