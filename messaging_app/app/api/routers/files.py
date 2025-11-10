from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.file import File as FileModel
from app.models.channel import Channel
from app.api.schemas.message import FilePublic, MessageSender
from app.dependencies import get_current_user
import os
import shutil
from datetime import datetime
import uuid


router = APIRouter()

# Directory where files will be stored
UPLOAD_DIR = "uploads/channels"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("/{channel_id}/upload", response_model=FilePublic, status_code=201)
async def upload_file(
    channel_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a file to a channel."""
    
    # Check if channel exists
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Check if user is a member of the channel
    if current_user not in channel.members:
        raise HTTPException(status_code=403, detail="Not a member of this channel")
    
    # Validate file size
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 50MB limit")
    
    try:
        # Create unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        
        # Create channel-specific directory if it doesn't exist
        channel_upload_dir = os.path.join(UPLOAD_DIR, channel_id)
        os.makedirs(channel_upload_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(channel_upload_dir, unique_filename)
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        # Create file record in database
        new_file = FileModel(
            channel_id=channel_id,
            sender_id=current_user.id,
            filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            file_type=file.content_type
        )
        db.add(new_file)
        db.commit()
        db.refresh(new_file)
        
        return {
            "id": str(new_file.id),
            "channel_id": str(new_file.channel_id),
            "sender_id": str(new_file.sender_id),
            "sender": {
                "id": str(current_user.id),
                "username": current_user.username,
                "email": current_user.email
            },
            "filename": new_file.filename,
            "file_type": new_file.file_type,
            "file_size": new_file.file_size,
            "created_at": new_file.created_at
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@router.get("/{channel_id}/files", response_model=list[FilePublic])
def get_channel_files(
    channel_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all files uploaded to a channel."""
    
    # Check if channel exists
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Check if user is a member of the channel
    if current_user not in channel.members:
        raise HTTPException(status_code=403, detail="Not a member of this channel")
    
    # Get files
    files = db.query(FileModel).filter(
        FileModel.channel_id == channel_id
    ).order_by(FileModel.created_at.desc()).all()
    
    return files


@router.get("/{channel_id}/files/{file_id}/download")
def download_file(
    channel_id: str,
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download a file from a channel."""
    from fastapi.responses import FileResponse
    
    # Check if channel exists
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Check if user is a member of the channel
    if current_user not in channel.members:
        raise HTTPException(status_code=403, detail="Not a member of this channel")
    
    # Get file
    file = db.query(FileModel).filter(
        FileModel.id == file_id,
        FileModel.channel_id == channel_id
    ).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    if not os.path.exists(file.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    return FileResponse(
        path=file.file_path,
        filename=file.filename,
        media_type=file.file_type
    )


@router.delete("/{channel_id}/files/{file_id}", status_code=200)
def delete_file(
    channel_id: str,
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a file (only uploader or channel creator can delete)."""
    
    # Check if channel exists
    channel = db.query(Channel).filter(Channel.id == channel_id).first()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    # Get file
    file = db.query(FileModel).filter(
        FileModel.id == file_id,
        FileModel.channel_id == channel_id
    ).first()
    
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Check permissions
    if file.sender_id != current_user.id and channel.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot delete this file")
    
    # Delete from disk
    if os.path.exists(file.file_path):
        os.remove(file.file_path)
    
    # Delete from database
    db.delete(file)
    db.commit()
    
    return {"message": "File deleted"}
