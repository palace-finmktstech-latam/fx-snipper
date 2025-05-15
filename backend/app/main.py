from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from core_logging.client import LogClient, EventType

app = FastAPI(title="FX Snipper")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the Core Logging client
logger = LogClient(
    app_name="FX Snipper",
    api_url="http://localhost:8001/api/",
    default_source="FX Snipper"
)

# Import routers
from app.api.endpoints import fx

# Include routers
app.include_router(fx.router, prefix="/api", tags=["fx"])