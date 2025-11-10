from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routers import auth, channels, messages, websocket, users, files, calendar, direct_messages


app = FastAPI(
    title="Messaging & Workflow App",
    version="0.1.0",
    debug=settings.DEBUG
)


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or ["http://localhost:3000"] for extra security
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
