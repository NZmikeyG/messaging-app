import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from app.config import settings
import logging

logger = logging.getLogger(__name__)


def init_sentry():
    """Initialize Sentry for error tracking and performance monitoring."""
    if not settings.SENTRY_DSN:
        logger.warning("Sentry DSN not configured - error tracking disabled")
        return
    
    try:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=0.1,  # 10% of transactions
            profiles_sample_rate=0.1,  # 10% of profiles
            environment=settings.ENVIRONMENT,
            release=settings.APP_VERSION,
            debug=settings.DEBUG,
        )
        logger.info("Sentry initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")
