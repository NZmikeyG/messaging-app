from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List
from datetime import datetime
from app.database import get_db
from app.models.user import User
from app.models.direct_message import DirectMessage
from app.api.schemas.direct_message import DirectMessageCreate, DirectMessageUpdate, DirectMessagePublic, DMUser
from app.dependencies import get_current_user


router = APIRouter()


@router.post("/", response_model=DirectMessagePublic, status_code=201)
def send_direct_message(
    dm: DirectMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a direct message to another user."""
    receiver = db.query(User).filter(User.id == dm.receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="Receiver not found")
    
    if dm.receiver_id == str(current_user.id):
        raise HTTPException(status_code=400, detail="Cannot send message to yourself")
    
    new_dm = DirectMessage(
        content=dm.content,
        sender_id=current_user.id,
        receiver_id=dm.receiver_id
    )
    db.add(new_dm)
    db.commit()
    db.refresh(new_dm)
    return new_dm


@router.get("/", response_model=List[DirectMessagePublic])
def get_direct_messages(
    other_user_id: str = Query(...),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get direct messages with a specific user."""
    other_user = db.query(User).filter(User.id == other_user_id).first()
    if not other_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    messages = db.query(DirectMessage).filter(
        or_(
            and_(DirectMessage.sender_id == current_user.id, DirectMessage.receiver_id == other_user_id),
            and_(DirectMessage.sender_id == other_user_id, DirectMessage.receiver_id == current_user.id)
        ),
        DirectMessage.is_deleted == False
    ).order_by(DirectMessage.created_at.desc()).offset(skip).limit(limit).all()
    
    for msg in messages:
        if msg.receiver_id == current_user.id and not msg.is_read:
            msg.is_read = True
    db.commit()
    
    return messages


@router.get("/conversations", response_model=List[DMUser])
def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of users the current user has conversations with."""
    sent_to = db.query(DirectMessage.receiver_id).filter(
        DirectMessage.sender_id == current_user.id
    ).distinct()
    
    received_from = db.query(DirectMessage.sender_id).filter(
        DirectMessage.receiver_id == current_user.id
    ).distinct()
    
    user_ids = set([str(uid[0]) for uid in sent_to] + [str(uid[0]) for uid in received_from])
    
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    return users


@router.put("/{dm_id}", response_model=DirectMessagePublic)
def update_direct_message(
    dm_id: str,
    dm_update: DirectMessageUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Edit a direct message."""
    dm = db.query(DirectMessage).filter(DirectMessage.id == dm_id).first()
    
    if not dm:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if dm.sender_id != current_user.id:
        raise HTTPException(status_code=403, detail="Can only edit your own messages")
    
    if dm.is_deleted:
        raise HTTPException(status_code=400, detail="Cannot edit deleted message")
    
    dm.content = dm_update.content
    dm.is_edited = True
    dm.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(dm)
    return dm


@router.delete("/{dm_id}", status_code=200)
def delete_direct_message(
    dm_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a direct message."""
    dm = db.query(DirectMessage).filter(DirectMessage.id == dm_id).first()
    
    if not dm:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if dm.sender_id != current_user.id:
        raise HTTPException(status_code=403, detail="Can only delete your own messages")
    
    dm.is_deleted = True
    dm.content = "[Message deleted]"
    dm.updated_at = datetime.utcnow()
    
    db.commit()
    return {"message": "Direct message deleted successfully"}
