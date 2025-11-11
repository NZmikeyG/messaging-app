from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.api.routers import auth, channels, messages, websocket, users, files, calendar, direct_messages, google_calendar
from app.logger import get_logger
from app.middleware.metrics import add_metrics_middleware
from app.middleware.error_tracking import init_sentry
from slowapi.errors import RateLimitExceeded
from app.api.routers import admin
from app.api.routers import advanced
import logging

logger = get_logger(__name__)

# Initialize Sentry
init_sentry()

# Create FastAPI app with comprehensive documentation
app = FastAPI(
    title="Messaging & Workflow App",
    version="1.0.0",
    description="""
    A real-time messaging platform with WebSocket support.
    
    ## Features
    
    * **User Management** - Register, login, profile management
    * **Channels** - Create, join, and manage channels
    * **Messaging** - Real-time message synchronization
    * **Direct Messages** - Private messaging with read receipts
    * **File Sharing** - Upload and share files in channels
    * **WebSocket** - Real-time typing indicators and presence
    * **Performance** - Redis caching and query optimization
    """,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

logger.info("✓ Starting Messaging & Workflow App")

# Rate limit exception handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(f"⚠ Rate limit exceeded for {request.client.host if request.client else 'unknown'}")
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later."}
    )

# Add CORS middleware FIRST
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add metrics middleware SECOND (with proper BaseHTTPMiddleware from Starlette)
app.add_middleware(BaseHTTPMiddleware, dispatch=add_metrics_middleware)

# Register routers with tags
tags_metadata = [
    {"name": "auth", "description": "Authentication endpoints - Register, login, profile"},
    {"name": "channels", "description": "Channel management - Create, join, manage channels"},
    {"name": "messages", "description": "Message operations - Send, edit, delete messages"},
    {"name": "direct-messages", "description": "Direct messaging - Private conversations"},
    {"name": "users", "description": "User management - Profiles, settings"},
    {"name": "files", "description": "File operations - Upload, download files"},
    {"name": "calendar", "description": "Calendar and events"},
    {"name": "websocket", "description": "Real-time WebSocket connections"},
]

app.openapi_tags = tags_metadata

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(channels.router, prefix="/api/channels", tags=["channels"])
app.include_router(messages.router, prefix="/api/messages", tags=["messages"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["calendar"])
app.include_router(websocket.router, prefix="/api", tags=["websocket"])
app.include_router(direct_messages.router, prefix="/api/direct-messages", tags=["direct-messages"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(advanced.router, prefix="/api/advanced", tags=["advanced"])

@app.get("/")
def root():
    """Root endpoint - API status."""
    return {"message": "Welcome to Messaging & Workflow App", "version": "1.0.0", "status": "running"}

@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint."""
    from prometheus_client import generate_latest
    return generate_latest()


