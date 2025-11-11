from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.calendar import GoogleDriveConnection, GoogleDriveFile, DriveAccessLog, DrivePermission
from app.models.user import User
from app.dependencies import get_current_user
from app.utils.google_drive import google_drive
from datetime import datetime
import logging
import os
import mimetypes

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/drive", tags=["google-drive"])


@router.get("/auth-url")
def get_drive_auth_url(current_user: User = Depends(get_current_user)):
    try:
        auth_url, state = google_drive.get_auth_url(str(current_user.id))
        return {"auth_url": auth_url, "state": state}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/callback")
def handle_drive_callback(code: str, team_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        tokens = google_drive.exchange_code_for_tokens(code)
        folder = google_drive.create_team_folder(tokens['access_token'], f"Team Drive - {team_id}")
        
        connection = GoogleDriveConnection(
            team_id=team_id,
            access_token=tokens['access_token'],
            refresh_token=tokens['refresh_token'],
            folder_id=folder['id'],
            folder_name=folder.get('name', 'Team Drive'),
            created_by=current_user.id
        )
        db.add(connection)
        db.commit()
        
        logger.info(f"Google Drive connected for team: {team_id}")
        return {"status": "connected", "folder_id": folder['id']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_id}/connection")
def get_connection_status(team_id: str, db: Session = Depends(get_db)):
    connection = db.query(GoogleDriveConnection).filter(GoogleDriveConnection.team_id == team_id).first()
    if not connection:
        return {"connected": False}
    return {"connected": True, "team_id": connection.team_id, "folder_name": connection.folder_name}


@router.post("/{team_id}/upload")
async def upload_file(team_id: str, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        connection = db.query(GoogleDriveConnection).filter(GoogleDriveConnection.team_id == team_id).first()
        if not connection or not connection.is_active:
            raise HTTPException(status_code=400, detail="Drive not connected")
        
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as f:
            f.write(await file.read())
        
        drive_file = google_drive.upload_file(connection.access_token, temp_path, file.filename, connection.folder_id)
        
        db_file = GoogleDriveFile(
            drive_id=connection.id,
            google_file_id=drive_file['id'],
            file_name=drive_file['name'],
            file_type=mimetypes.guess_extension(drive_file.get('mimeType', '')).strip('.') or 'other',
            file_size=int(drive_file.get('size', 0)),
            mime_type=drive_file.get('mimeType'),
            uploaded_by=current_user.id,
            google_web_view_link=drive_file.get('webViewLink')
        )
        db.add(db_file)
        
        access_log = DriveAccessLog(drive_id=connection.id, file_id=db_file.id, user_id=current_user.id, action="upload", status="success")
        db.add(access_log)
        db.commit()
        
        os.remove(temp_path)
        logger.info(f"File uploaded: {file.filename}")
        return {"id": str(db_file.id), "file_name": db_file.file_name, "size": db_file.file_size}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_id}/files")
def list_files(team_id: str, db: Session = Depends(get_db)):
    connection = db.query(GoogleDriveConnection).filter(GoogleDriveConnection.team_id == team_id).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Drive not connected")
    
    files = db.query(GoogleDriveFile).filter(GoogleDriveFile.drive_id == connection.id).all()
    return [{"id": str(f.id), "name": f.file_name, "size": f.file_size, "type": f.file_type, "uploaded": f.uploaded_at.isoformat()} for f in files]


@router.delete("/{team_id}/files/{file_id}", status_code=204)
def delete_file(team_id: str, file_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        connection = db.query(GoogleDriveConnection).filter(GoogleDriveConnection.team_id == team_id).first()
        if not connection:
            raise HTTPException(status_code=404, detail="Drive not connected")
        
        file = db.query(GoogleDriveFile).filter(GoogleDriveFile.id == file_id).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        google_drive.delete_file(connection.access_token, file.google_file_id)
        
        access_log = DriveAccessLog(drive_id=connection.id, file_id=file.id, user_id=current_user.id, action="delete", status="success")
        db.add(access_log)
        db.delete(file)
        db.commit()
        
        logger.info(f"File deleted: {file_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{team_id}/files/{file_id}/share/{email}")
def share_file(team_id: str, file_id: str, email: str, role: str = "reader", db: Session = Depends(get_db)):
    try:
        connection = db.query(GoogleDriveConnection).filter(GoogleDriveConnection.team_id == team_id).first()
        if not connection:
            raise HTTPException(status_code=404, detail="Drive not connected")
        
        file = db.query(GoogleDriveFile).filter(GoogleDriveFile.id == file_id).first()
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        google_drive.share_file(connection.access_token, file.google_file_id, email, role)
        logger.info(f"File shared: {file_id} with {email}")
        return {"status": "shared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_id}/access-logs")
def get_access_logs(team_id: str, limit: int = 50, db: Session = Depends(get_db)):
    connection = db.query(GoogleDriveConnection).filter(GoogleDriveConnection.team_id == team_id).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Drive not connected")
    
    logs = db.query(DriveAccessLog).filter(DriveAccessLog.drive_id == connection.id).order_by(DriveAccessLog.created_at.desc()).limit(limit).all()
    return [{"action": l.action, "user_id": str(l.user_id), "status": l.status, "created": l.created_at.isoformat()} for l in logs]


@router.post("/{team_id}/permissions/{user_id}")
def grant_permission(team_id: str, user_id: str, permission_level: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    connection = db.query(GoogleDriveConnection).filter(GoogleDriveConnection.team_id == team_id).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Drive not connected")
    
    permission = DrivePermission(drive_id=connection.id, user_id=user_id, permission_level=permission_level, granted_by=current_user.id)
    db.add(permission)
    db.commit()
    logger.info(f"Permission granted: {user_id} -> {permission_level}")
    return {"status": "granted", "permission_level": permission_level}
