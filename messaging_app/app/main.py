from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routers import auth, channels, messages, websocket, users, files, calendar, direct_messages
from app.logger import get_logger
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse


logger = get_logger(__name__)


app = FastAPI(
    title="Messaging & Workflow App",
    version="0.1.0",
    debug=settings.DEBUG
)


# Log startup
logger.info("Starting Messaging & Workflow App")


# Add rate limit exception handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    logger.warning(f"Rate limit exceeded for {request.client.host if request.client else 'unknown'}")
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later."}
    )


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register all routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(channels.router, prefix="/api/channels", tags=["channels"])
app.include_router(messages.router, prefix="/api/messages", tags=["messages"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["calendar"])
app.include_router(websocket.router, prefix="/api", tags=["websocket"])
app.include_router(direct_messages.router, prefix="/api/direct-messages", tags=["direct-messages"])


@app.get("/")
def root():
    return {"message": "Welcome to Messaging & Workflow App"}
