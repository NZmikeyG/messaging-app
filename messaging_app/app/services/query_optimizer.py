from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_
from app.models.channel import Channel
from app.models.message import Message
from app.models.user import User
from app.models.direct_message import DirectMessage
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

__all__ = ['QueryOptimizer']


class QueryOptimizer:
    """Optimize database queries with eager loading and caching."""
    
    @staticmethod
    def get_channel_with_details(db: Session, channel_id):
        """Get channel with optimized loading of related data."""
        try:
            channel = db.query(Channel).options(
                joinedload(Channel.members),
                joinedload(Channel.creator),
                selectinload(Channel.messages).joinedload('user')
            ).filter(Channel.id == channel_id).first()
            logger.debug(f"Loaded channel {channel_id} with optimized queries")
            return channel
        except Exception as e:
            logger.error(f"Error loading channel {channel_id}: {e}")
            return None
    
    @staticmethod
    def get_messages_with_users(db: Session, channel_id, limit: int = 50, offset: int = 0):
        """Get messages with eager-loaded user data."""
        try:
            messages = db.query(Message).options(
                joinedload('user')
            ).filter(
                Message.channel_id == channel_id,
                Message.is_deleted == False
            ).order_by(Message.created_at.desc()).offset(offset).limit(limit).all()
            logger.debug(f"Loaded {len(messages)} messages for channel {channel_id}")
            return messages
        except Exception as e:
            logger.error(f"Error loading messages: {e}")
            return []
    
    @staticmethod
    def get_user_channels(db: Session, user_id):
        """Get all channels for a user with optimized queries."""
        try:
            channels = db.query(Channel).filter(
                Channel.members.any(id=user_id)
            ).options(
                joinedload(Channel.members),
                joinedload(Channel.creator)
            ).all()
            logger.debug(f"Loaded {len(channels)} channels for user {user_id}")
            return channels
        except Exception as e:
            logger.error(f"Error loading user channels: {e}")
            return []
    
    @staticmethod
    def get_direct_messages_optimized(db: Session, user_id_1, user_id_2, limit: int = 50, offset: int = 0):
        """Get DMs with optimized queries."""
        try:
            messages = db.query(DirectMessage).options(
                joinedload('sender'),
                joinedload('receiver')
            ).filter(
                or_(
                    and_(DirectMessage.sender_id == user_id_1, DirectMessage.receiver_id == user_id_2),
                    and_(DirectMessage.sender_id == user_id_2, DirectMessage.receiver_id == user_id_1)
                ),
                DirectMessage.is_deleted == False
            ).order_by(DirectMessage.created_at.desc()).offset(offset).limit(limit).all()
            logger.debug(f"Loaded {len(messages)} DMs")
            return messages
        except Exception as e:
            logger.error(f"Error loading DMs: {e}")
            return []
