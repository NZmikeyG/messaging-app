from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.user import User
from app.models.channel import Channel
from app.models.message import Message
from app.api.schemas.message import MessageCreate, MessageUpdate, MessagePublic
from app.dependencies import get_current_user
from datetime import datetime


router = APIRouter()


@router.post("/{channel_id}/messages", response_model=MessagePublic, status_code=201)
def create_message(
    channel_id: str,
    message: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if current_user not in channel.members:
        raise HTTPException(status_code=403, detail="Not a member of this channel")

    new_message = Message(
        content=message.content,
        channel_id=channel_id,
        user_id=current_user.id
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    return new_message


@router.get("/{channel_id}/messages", response_model=List[MessagePublic])
def get_messages(
    channel_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    if current_user not in channel.members:
        raise HTTPException(status_code=403, detail="Not a member of this channel")

    messages = db.query(Message).filter(
        Message.channel_id == channel_id,
        Message.is_deleted == False
    ).order_by(Message.created_at.desc()).offset(skip).limit(limit).all()
    return messages


@router.put("/messages/{message_id}", response_model=MessagePublic)
def update_message(
    message_id: str,
    message_update: MessageUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    if message.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Can only edit your own messages")

    if message.is_deleted:
        raise HTTPException(status_code=400, detail="Cannot edit a deleted message")

    message.content = message_update.content
    message.is_edited = True
    message.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(message)

    return message


@router.delete("/messages/{message_id}", status_code=200)
def delete_message(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    if message.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Can only delete your own messages")

    message.is_deleted = True
    message.content = "[Message deleted]"
    message.updated_at = datetime.utcnow()

    db.commit()

    return {"message": "Message deleted successfully"}
