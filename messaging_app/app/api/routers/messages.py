from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.message import Message
from app.models.channel import Channel
from app.api.schemas.message import MessageCreate, MessagePublic
from app.dependencies import get_current_user


router = APIRouter()


@router.post("/{channel_id}", response_model=MessagePublic, status_code=201)
def send_message(
    channel_id: str,
    message: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message to a channel."""
    # Check if channel exists
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Check if user is a member of the channel
    if current_user not in channel.members:
        raise HTTPException(status_code=403, detail="Not a member of this channel")
    
    # Create message
    new_message = Message(
        channel_id=channel_id,
        sender_id=current_user.id,
        content=message.content
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    return new_message


@router.get("/{channel_id}", response_model=list[MessagePublic])
def get_messages(
    channel_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all messages from a channel."""
    # Check if channel exists
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Check if user is a member of the channel
    if current_user not in channel.members:
        raise HTTPException(status_code=403, detail="Not a member of this channel")
    
    # Get messages
    messages = db.query(Message).filter(
        Message.channel_id == channel_id
    ).order_by(Message.created_at.asc()).all()
    
    return messages


@router.get("/{channel_id}/{message_id}", response_model=MessagePublic)
def get_message(
    channel_id: str,
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific message."""
    # Check if channel exists
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Check if user is a member of the channel
    if current_user not in channel.members:
        raise HTTPException(status_code=403, detail="Not a member of this channel")
    
    # Get message
    message = db.query(Message).filter(
        Message.id == message_id,
        Message.channel_id == channel_id
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return message


@router.delete("/{channel_id}/{message_id}", status_code=200)
def delete_message(
    channel_id: str,
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a message (only sender or channel creator can delete)."""
    # Check if channel exists
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Get message
    message = db.query(Message).filter(
        Message.id == message_id,
        Message.channel_id == channel_id
    ).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Check permissions
    if message.sender_id != current_user.id and channel.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot delete this message")
    
    db.delete(message)
    db.commit()
    return {"message": "Message deleted"}
