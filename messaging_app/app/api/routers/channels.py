from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from uuid import UUID
from typing import List
import logging

from app.database import get_db
from app.models.user import User
from app.models.channel import Channel
from app.api.schemas.channel import ChannelCreate, ChannelUpdate, ChannelPublic, ChannelMember
from app.dependencies import get_current_user
from app.services.cache_service import cache_service
from app.services.query_optimizer import QueryOptimizer
from app.middleware.metrics import (
    http_requests_total, 
    cache_hits, 
    cache_misses,
    http_request_duration_seconds
)
import time

logger = logging.getLogger(__name__)

router = APIRouter()


# ============ CHANNEL OPERATIONS ============

@router.post("/", response_model=ChannelPublic, status_code=201)
async def create_channel(
    channel: ChannelCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new channel.
    
    - **name**: Channel name (required)
    - **description**: Channel description (optional)
    
    Returns the created channel details.
    """
    start_time = time.time()
    
    try:
        logger.info(f"Creating channel '{channel.name}' by user {current_user.username}")
        
        # Check if channel name already exists
        existing = db.query(Channel).filter(Channel.name == channel.name).first()
        if existing:
            logger.warning(f"Channel creation failed - name '{channel.name}' already exists")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Channel name already exists"
            )
        
        # Create new channel
        new_channel = Channel(
            name=channel.name,
            description=channel.description,
            creator_id=current_user.id
        )
        new_channel.members.append(current_user)
        
        db.add(new_channel)
        db.commit()
        db.refresh(new_channel)
        
        # Invalidate user's channel cache
        await cache_service.invalidate_user_cache(str(current_user.id))
        
        logger.info(f"Channel '{channel.name}' created successfully with ID {new_channel.id}")
        
        return {
            "id": str(new_channel.id),
            "name": new_channel.name,
            "description": new_channel.description,
            "member_count": len(new_channel.members),
            "created_at": new_channel.created_at,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating channel: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create channel"
        )
    finally:
        duration = time.time() - start_time
        if duration > 1.0:
            logger.warning(f"Slow request: create_channel took {duration:.2f}s")


@router.get("/", response_model=List[ChannelPublic])
async def list_channels(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all channels the user is a member of.
    
    - **skip**: Number of channels to skip (pagination)
    - **limit**: Maximum number of channels to return (1-100)
    
    Results are cached for 10 minutes for performance.
    """
    start_time = time.time()
    
    try:
        cache_key = f"user:{current_user.id}:channels:list"
        
        # Try to get from cache
        cached_channels = await cache_service.get(cache_key)
        if cached_channels:
            logger.debug(f"Returning cached channels for user {current_user.id}")
            cache_hits.labels(cache_type="channels").inc()
            return cached_channels
        
        cache_misses.labels(cache_type="channels").inc()
        
        logger.debug(f"Fetching channels for user {current_user.id} from database")
        
        # Use optimized query
        channels = QueryOptimizer.get_user_channels(db, current_user.id)
        
        # Convert to response format
        result = [
            {
                "id": str(ch.id),
                "name": ch.name,
                "description": ch.description,
                "member_count": len(ch.members),
                "created_at": ch.created_at,
            }
            for ch in channels[skip:skip + limit]
        ]
        
        # Cache the result (10 minutes)
        await cache_service.set(cache_key, result, ttl=600)
        
        logger.info(f"Retrieved {len(result)} channels for user {current_user.id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error listing channels: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve channels"
        )
    finally:
        duration = time.time() - start_time
        if duration > 1.0:
            logger.warning(f"Slow request: list_channels took {duration:.2f}s")


@router.get("/{channel_id}", response_model=ChannelPublic)
async def get_channel(
    channel_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific channel with full details.
    
    - **channel_id**: Channel ID (UUID)
    
    Returns channel details including member information.
    Requires user to be a member of the channel.
    """
    start_time = time.time()
    
    try:
        # Validate UUID format
        try:
            channel_uuid = UUID(channel_id)
        except ValueError:
            logger.warning(f"Invalid channel ID format: {channel_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid channel ID format"
            )
        
        cache_key = f"channel:{channel_id}:details"
        
        # Try cache first
        cached_channel = await cache_service.get(cache_key)
        if cached_channel:
            # Verify user is still a member
            user_id_list = cached_channel.get("member_ids", [])
            if str(current_user.id) in user_id_list:
                logger.debug(f"Returning cached channel {channel_id}")
                cache_hits.labels(cache_type="channel_details").inc()
                return cached_channel
        
        cache_misses.labels(cache_type="channel_details").inc()
        
        # Fetch from database with optimization
        channel = QueryOptimizer.get_channel_with_details(db, channel_uuid)
        
        if not channel:
            logger.warning(f"Channel {channel_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found"
            )
        
        # Check membership
        if current_user not in channel.members:
            logger.warning(f"User {current_user.id} attempted to access non-member channel {channel_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this channel"
            )
        
        result = {
            "id": str(channel.id),
            "name": channel.name,
            "description": channel.description,
            "member_count": len(channel.members),
            "member_ids": [str(m.id) for m in channel.members],
            "created_at": channel.created_at,
        }
        
        # Cache result (5 minutes)
        await cache_service.set(cache_key, result, ttl=300)
        
        logger.info(f"Retrieved channel {channel_id}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting channel {channel_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve channel"
        )
    finally:
        duration = time.time() - start_time
        if duration > 1.0:
            logger.warning(f"Slow request: get_channel took {duration:.2f}s")


# ============ MEMBER MANAGEMENT ============

@router.post("/{channel_id}/members/{user_id}", status_code=201)
async def add_member_to_channel(
    channel_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a user to a channel.
    
    - **channel_id**: Channel ID (UUID)
    - **user_id**: User ID to add (UUID)
    
    Only the channel creator can add members.
    """
    start_time = time.time()
    
    try:
        # Validate UUIDs
        try:
            channel_uuid = UUID(channel_id)
            user_uuid = UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ID format"
            )
        
        logger.info(f"Adding user {user_id} to channel {channel_id}")
        
        # Get channel
        channel = db.query(Channel).filter(Channel.id == channel_uuid).first()
        if not channel:
            logger.warning(f"Channel {channel_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found"
            )
        
        # Check authorization
        if channel.creator_id != current_user.id:
            logger.warning(f"User {current_user.id} attempted to add member without permission")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only channel creator can add members"
            )
        
        # Get user to add
        user_to_add = db.query(User).filter(User.id == user_uuid).first()
        if not user_to_add:
            logger.warning(f"User {user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if already member
        if user_to_add in channel.members:
            logger.warning(f"User {user_id} already in channel {channel_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already in channel"
            )
        
        # Add member
        channel.members.append(user_to_add)
        db.commit()
        
        # Invalidate caches
        await cache_service.invalidate_channel_cache(channel_id)
        await cache_service.invalidate_user_cache(str(user_to_add.id))
        
        logger.info(f"User {user_id} added to channel {channel_id}")
        
        return {
            "message": "User added to channel",
            "channel_id": channel_id,
            "user_id": user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding member to channel: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add member"
        )
    finally:
        duration = time.time() - start_time
        if duration > 1.0:
            logger.warning(f"Slow request: add_member_to_channel took {duration:.2f}s")


@router.delete("/{channel_id}/members/{user_id}", status_code=200)
async def remove_member_from_channel(
    channel_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Remove a user from a channel.
    
    - **channel_id**: Channel ID (UUID)
    - **user_id**: User ID to remove (UUID)
    
    Channel creator can remove any member.
    Users can remove themselves.
    """
    start_time = time.time()
    
    try:
        # Validate UUIDs
        try:
            channel_uuid = UUID(channel_id)
            user_uuid = UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid ID format"
            )
        
        logger.info(f"Removing user {user_id} from channel {channel_id}")
        
        # Get channel
        channel = db.query(Channel).filter(Channel.id == channel_uuid).first()
        if not channel:
            logger.warning(f"Channel {channel_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found"
            )
        
        # Check authorization
        is_creator = channel.creator_id == current_user.id
        is_self = current_user.id == user_uuid
        
        if not (is_creator or is_self):
            logger.warning(f"User {current_user.id} not authorized to remove member")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot remove this member"
            )
        
        # Get user to remove
        user_to_remove = db.query(User).filter(User.id == user_uuid).first()
        if not user_to_remove:
            logger.warning(f"User {user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if member
        if user_to_remove not in channel.members:
            logger.warning(f"User {user_id} not in channel {channel_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not in channel"
            )
        
        # Remove member
        channel.members.remove(user_to_remove)
        db.commit()
        
        # Invalidate caches
        await cache_service.invalidate_channel_cache(channel_id)
        await cache_service.invalidate_user_cache(str(user_to_remove.id))
        
        logger.info(f"User {user_id} removed from channel {channel_id}")
        
        return {
            "message": "User removed from channel",
            "channel_id": channel_id,
            "user_id": user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing member from channel: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove member"
        )
    finally:
        duration = time.time() - start_time
        if duration > 1.0:
            logger.warning(f"Slow request: remove_member_from_channel took {duration:.2f}s")


# ============ CHANNEL MANAGEMENT ============

@router.put("/{channel_id}", response_model=ChannelPublic)
async def update_channel(
    channel_id: str,
    channel_update: ChannelUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update channel details.
    
    - **channel_id**: Channel ID (UUID)
    - **name**: New channel name (optional)
    - **description**: New description (optional)
    
    Only channel creator can update channel.
    """
    start_time = time.time()
    
    try:
        try:
            channel_uuid = UUID(channel_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid channel ID format"
            )
        
        logger.info(f"Updating channel {channel_id}")
        
        channel = db.query(Channel).filter(Channel.id == channel_uuid).first()
        if not channel:
            logger.warning(f"Channel {channel_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found"
            )
        
        if channel.creator_id != current_user.id:
            logger.warning(f"User {current_user.id} not authorized to update channel")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only channel creator can update channel"
            )
        
        # Update fields
        if channel_update.name:
            channel.name = channel_update.name
        if channel_update.description is not None:
            channel.description = channel_update.description
        
        db.commit()
        db.refresh(channel)
        
        # Invalidate cache
        await cache_service.invalidate_channel_cache(channel_id)
        
        logger.info(f"Channel {channel_id} updated successfully")
        
        return {
            "id": str(channel.id),
            "name": channel.name,
            "description": channel.description,
            "member_count": len(channel.members),
            "created_at": channel.created_at,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating channel: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update channel"
        )
    finally:
        duration = time.time() - start_time
        if duration > 1.0:
            logger.warning(f"Slow request: update_channel took {duration:.2f}s")


@router.delete("/{channel_id}", status_code=204)
async def delete_channel(
    channel_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a channel.
    
    - **channel_id**: Channel ID (UUID)
    
    Only channel creator can delete channel.
    This will remove all messages in the channel.
    """
    start_time = time.time()
    
    try:
        try:
            channel_uuid = UUID(channel_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid channel ID format"
            )
        
        logger.info(f"Deleting channel {channel_id}")
        
        channel = db.query(Channel).filter(Channel.id == channel_uuid).first()
        if not channel:
            logger.warning(f"Channel {channel_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found"
            )
        
        if channel.creator_id != current_user.id:
            logger.warning(f"User {current_user.id} not authorized to delete channel")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only channel creator can delete channel"
            )
        
        # Get all member IDs for cache invalidation
        member_ids = [str(m.id) for m in channel.members]
        
        # Delete channel
        db.delete(channel)
        db.commit()
        
        # Invalidate caches for all members
        await cache_service.invalidate_channel_cache(channel_id)
        for member_id in member_ids:
            await cache_service.invalidate_user_cache(member_id)
        
        logger.info(f"Channel {channel_id} deleted successfully")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting channel: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete channel"
        )
    finally:
        duration = time.time() - start_time
        if duration > 1.0:
            logger.warning(f"Slow request: delete_channel took {duration:.2f}s")
