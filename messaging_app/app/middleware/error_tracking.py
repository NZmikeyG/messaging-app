import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from app.config import settings
import logging

logger = logging.getLogger(__name__)


def init_sentry():
    """Initialize Sentry for error tracking and performance monitoring."""
    if not getattr(settings, 'SENTRY_DSN', None):
        logger.info("ℹ Sentry not configured - error tracking disabled")
        return
    
    try:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
            environment=getattr(settings, 'ENVIRONMENT', 'development'),
            release=getattr(settings, 'APP_VERSION', '1.0.0'),
            debug=getattr(settings, 'DEBUG', False),
        )
        logger.info("✓ Sentry initialized successfully")
    except Exception as e:
        logger.warning(f"⚠ Failed to initialize Sentry: {e}")
