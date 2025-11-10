from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID, UUID as UUIDType
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.message import Message
from app.models.message_reaction import MessageReaction
from app.api.schemas.message import (
    MessageCreate, MessageUpdate, MessagePublic,
    MessageReactionCreate, MessageReactionPublic
)

router = APIRouter()


@router.post("/", response_model=MessagePublic, status_code=201)
def create_message(
    message: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new message in a channel or reply to a message."""
    
    # Validate parent if provided
    parent = None
    if message.parent_id:
        try:
            parent_uuid = UUID(message.parent_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid parent ID format")
        parent = db.query(Message).filter(Message.id == parent_uuid).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent message not found")
    
    new_message = Message(
        content=message.content,
        channel_id=parent.channel_id if parent else None,
        user_id=current_user.id,
        parent_id=parent.id if parent else None
    )
    if not new_message.channel_id:
        raise HTTPException(status_code=400, detail="Channel ID is required if no parent message")

    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    return new_message


@router.get("/", response_model=List[MessagePublic])
def get_messages(
    channel_id: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get messages from a channel with pagination."""
    try:
        channel_uuid = UUID(channel_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid channel ID format")

    messages = db.query(Message).filter(
        Message.channel_id == channel_uuid,
        Message.is_deleted == False
    ).order_by(Message.created_at.desc()).offset(skip).limit(limit).all()

    return messages


@router.put("/{message_id}", response_model=MessagePublic)
def update_message(
    message_id: str,
    message_update: MessageUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the content of a message. Only owner allowed."""
    try:
        msg_uuid = UUID(message_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid message ID format")
    
    message = db.query(Message).filter(Message.id == msg_uuid).first()
    if not message or message.is_deleted:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if message.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this message")
    
    message.content = message_update.content
    db.commit()
    db.refresh(message)
    return message


@router.post("/{message_id}/reactions", response_model=MessageReactionPublic, status_code=201)
def add_reaction(
    message_id: str,
    reaction: MessageReactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a reaction (emoji) to a message by the current user."""
    try:
        msg_uuid = UUID(message_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid message ID format")
    
    message = db.query(Message).filter(Message.id == msg_uuid).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    existing = db.query(MessageReaction).filter(
        MessageReaction.message_id == msg_uuid,
        MessageReaction.user_id == current_user.id,
        MessageReaction.emoji == reaction.emoji,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Reaction already exists")
    
    new_reaction = MessageReaction(
        message_id=msg_uuid,
        user_id=current_user.id,
        emoji=reaction.emoji,
    )
    db.add(new_reaction)
    db.commit()
    db.refresh(new_reaction)
    return new_reaction


@router.delete("/{message_id}/reactions", status_code=204)
def remove_reaction(
    message_id: str,
    emoji: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a reaction (emoji) from a message by the current user."""
    try:
        msg_uuid = UUID(message_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid message ID format")
    
    reaction = db.query(MessageReaction).filter(
        MessageReaction.message_id == msg_uuid,
        MessageReaction.user_id == current_user.id,
        MessageReaction.emoji == emoji,
    ).first()
    
    if not reaction:
        raise HTTPException(status_code=404, detail="Reaction not found")
    
    db.delete(reaction)
    db.commit()
    return None
