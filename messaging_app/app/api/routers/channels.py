from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.channel import Channel, channel_members
from app.api.schemas.channel import ChannelCreate, ChannelUpdate, ChannelPublic
from app.dependencies import get_current_user


router = APIRouter()


@router.post("/", response_model=ChannelPublic, status_code=201)
def create_channel(
    channel: ChannelCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new channel."""
    if db.query(Channel).filter(Channel.name == channel.name).first():
        raise HTTPException(status_code=400, detail="Channel name already exists")
    
    new_channel = Channel(
        name=channel.name,
        description=channel.description,
        creator_id=current_user.id
    )
    new_channel.members.append(current_user)
    db.add(new_channel)
    db.commit()
    db.refresh(new_channel)
    return new_channel


@router.get("/", response_model=list[ChannelPublic])
def list_channels(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all channels the user is a member of."""
    channels = db.query(Channel).filter(
        Channel.members.any(User.id == current_user.id)
    ).all()
    return channels


@router.get("/{channel_id}", response_model=ChannelPublic)
def get_channel(
    channel_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific channel."""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if current_user not in channel.members:
        raise HTTPException(status_code=403, detail="Not a member of this channel")
    
    return channel


@router.post("/{channel_id}/members/{user_id}", status_code=201)
def add_member_to_channel(
    channel_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a user to a channel."""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if channel.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only channel creator can add members")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user in channel.members:
        raise HTTPException(status_code=400, detail="User already in channel")
    
    channel.members.append(user)
    db.commit()
    return {"message": "User added to channel"}


@router.delete("/{channel_id}/members/{user_id}", status_code=200)
def remove_member_from_channel(
    channel_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a user from a channel."""
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    if channel.creator_id != current_user.id and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Cannot remove this member")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user not in channel.members:
        raise HTTPException(status_code=400, detail="User not in channel")
    
    channel.members.remove(user)
    db.commit()
    return {"message": "User removed from channel"}
