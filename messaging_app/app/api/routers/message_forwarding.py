from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.message import Message
from app.models.user import User
from app.dependencies import get_current_user
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/messages", tags=["message-forwarding"])


@router.post("/{message_id}/forward/thread/{target_thread_id}")
def forward_to_thread(message_id: str, target_thread_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    '''Forward a message to another thread'''
    original_msg = db.query(Message).filter(Message.id == message_id).first()
    if not original_msg:
        raise HTTPException(status_code=404, detail="Message not found")

    target_msg = db.query(Message).filter(Message.id == target_thread_id).first()
    if not target_msg:
        raise HTTPException(status_code=404, detail="Target thread not found")

    # Create forwarded copy
    forwarded = Message(
        channel_id=target_msg.channel_id,
        user_id=current_user.id,
        content=f"**Forwarded from:** {original_msg.user.email}\n\n{original_msg.content}",
        parent_id=target_thread_id,
        forwarded_from_id=original_msg.id,
        forwarded_from_channel_id=original_msg.channel_id,
        forwarded_by=current_user.id,
        forwarded_at=datetime.utcnow()
    )

    db.add(forwarded)
    db.commit()
    db.refresh(forwarded)

    logger.info(f"Message {message_id} forwarded to thread {target_thread_id}")
    return {
        "status": "forwarded",
        "forwarded_message_id": str(forwarded.id),
        "original_message_id": str(original_msg.id),
        "forwarded_at": forwarded.forwarded_at.isoformat()
    }


@router.get("/{message_id}/forwards")
def get_message_forwards(message_id: str, db: Session = Depends(get_db)):
    '''Get all forwards of a message'''
    original = db.query(Message).filter(Message.id == message_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Message not found")

    forwards = db.query(Message).filter(Message.forwarded_from_id == message_id).all()

    return {
        "original_message_id": str(original.id),
        "total_forwards": len(forwards),
        "forwards": [{
            "id": str(f.id),
            "forwarded_by": f.forwarder.email,
            "forwarded_to_channel": f.channel.name,
            "forwarded_at": f.forwarded_at.isoformat()
        } for f in forwards]
    }
