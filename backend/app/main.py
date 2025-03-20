from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from core_logging.client import LogClient, EventType

app = FastAPI(title="Swap Snipper")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the Core Logging client
logger = LogClient(
    app_name="Swap Snipper",
    api_url="http://localhost:8001/api/",
    default_source="Swap Snipper"
)

# Import routers
from app.api.endpoints import swaps

# Include routers
app.include_router(swaps.router, prefix="/api", tags=["swaps"])