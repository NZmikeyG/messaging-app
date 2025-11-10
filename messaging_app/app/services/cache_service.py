import redis
import json
from typing import Optional, Any
import logging
from app.config import settings

logger = logging.getLogger(__name__)

__all__ = ['cache_service']


class CacheService:
    """Redis caching service for performance optimization."""
    
    def __init__(self):
        self.redis = None
        self.connected = False
        
        try:
            redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379')
            self.redis = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=3)
            self.redis.ping()
            self.connected = True
            logger.info("✓ Redis connection established")
        except redis.ConnectionError as e:
            logger.warning(f"⚠ Redis connection failed: {e}. Caching disabled.")
            self.redis = None
            self.connected = False
        except Exception as e:
            logger.warning(f"⚠ Failed to initialize Redis: {e}. Caching disabled.")
            self.redis = None
            self.connected = False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.connected or not self.redis:
            return None
        
        try:
            value = self.redis.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            logger.debug(f"Cache MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"Error getting cache {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL (1 hour default)."""
        if not self.connected or not self.redis:
            return False
        
        try:
            self.redis.setex(key, ttl, json.dumps(value))
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Error setting cache {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete from cache."""
        if not self.connected or not self.redis:
            return False
        
        try:
            self.redis.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
        except Exception as e:
            logger.error(f"Error deleting cache {key}: {e}")
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        if not self.connected or not self.redis:
            return 0
        
        try:
            keys = self.redis.keys(pattern)
            if keys:
                deleted = self.redis.delete(*keys)
                logger.debug(f"Cache INVALIDATE: {pattern} ({deleted} keys deleted)")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Error invalidating cache pattern {pattern}: {e}")
            return 0
    
    async def invalidate_user_cache(self, user_id: str) -> int:
        """Invalidate all user-related cache."""
        return await self.invalidate_pattern(f"user:{user_id}:*")
    
    async def invalidate_channel_cache(self, channel_id: str) -> int:
        """Invalidate all channel-related cache."""
        return await self.invalidate_pattern(f"channel:{channel_id}:*")
    
    async def clear_all(self) -> bool:
        """Clear all cache (use carefully!)."""
        if not self.connected or not self.redis:
            return False
        
        try:
            self.redis.flushdb()
            logger.warning("Cache CLEARED (all keys deleted)")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False


# Global cache service instance - gracefully handles Redis unavailability
cache_service = CacheService()
