from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

# Create limiter instance
limiter = Limiter(key_func=get_remote_address)


# Rate limit configurations
RATE_LIMITS = {
    "auth": "5/minute",           # 5 requests per minute
    "message": "50/minute",       # 50 messages per minute
    "channel": "20/minute",       # 20 channel operations per minute
    "file": "10/minute",          # 10 file uploads per minute
    "general": "100/minute",      # 100 general requests per minute
}
