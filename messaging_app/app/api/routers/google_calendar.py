from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.calendar import GoogleCalendarSync, Calendar, CalendarEvent
from app.models.user import User
from app.dependencies import get_current_user
from app.utils.google_calendar import google_calendar
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/calendar/google", tags=["google-calendar"])


@router.get("/auth-url")
def get_google_auth_url(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    '''Get Google OAuth2 authorization URL'''
    try:
        auth_url, state = google_calendar.get_auth_url(str(current_user.id))
        return {"auth_url": auth_url, "state": state}
    except Exception as e:
        logger.error(f"Error getting auth URL: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get auth URL")


@router.post("/callback")
def handle_google_callback(code: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    '''Handle Google OAuth2 callback'''
    try:
        # Exchange code for tokens
        tokens = google_calendar.exchange_code_for_tokens(code)
        
        # Get user's calendar list to find primary calendar
        calendars = google_calendar.get_calendar_list(tokens['access_token'])
        primary_calendar = next((c for c in calendars if c.get('primary')), calendars[0] if calendars else None)
        
        if not primary_calendar:
            raise HTTPException(status_code=400, detail="No calendar found")
        
        # Save sync configuration
        sync = GoogleCalendarSync(
            user_id=current_user.id,
            google_calendar_id=primary_calendar['id'],
            google_access_token=tokens['access_token'],
            google_refresh_token=tokens['refresh_token'],
            sync_enabled=True
        )
        
        db.add(sync)
        db.commit()
        
        logger.info(f"Google Calendar synced for user: {current_user.email}")
        return {"status": "connected", "calendar_name": primary_calendar['summary']}
    except Exception as e:
        logger.error(f"Error in callback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
def sync_google_calendar(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    '''Sync events from Google Calendar'''
    try:
        sync = db.query(GoogleCalendarSync).filter(GoogleCalendarSync.user_id == current_user.id).first()
        
        if not sync:
            raise HTTPException(status_code=404, detail="Google Calendar not connected")
        
        if not sync.sync_enabled:
            raise HTTPException(status_code=400, detail="Sync is disabled")
        
        # Get events from Google
        events = google_calendar.sync_calendar_events(
            sync.google_access_token,
            sync.google_calendar_id
        )
        
        # Create or update calendar if doesn't exist
        if not sync.calendar_id:
            calendar = Calendar(
                owner_id=current_user.id,
                name=f"Google Calendar",
                color="#4285F4",
                is_public=False
            )
            db.add(calendar)
            db.commit()
            db.refresh(calendar)
            sync.calendar_id = calendar.id
            db.commit()
        
        # Import events
        imported_count = 0
        for event in events:
            existing = db.query(CalendarEvent).filter(
                CalendarEvent.google_event_id == event['id']
            ).first()
            
            if not existing:
                start = event.get('start', {})
                end = event.get('end', {})
                
                start_time = start.get('dateTime') or start.get('date')
                end_time = end.get('dateTime') or end.get('date')
                
                if start_time and end_time:
                    cal_event = CalendarEvent(
                        calendar_id=sync.calendar_id,
                        created_by=current_user.id,
                        title=event.get('summary', 'Untitled'),
                        description=event.get('description'),
                        start_time=datetime.fromisoformat(start_time.replace('Z', '+00:00')) if isinstance(start_time, str) else start_time,
                        end_time=datetime.fromisoformat(end_time.replace('Z', '+00:00')) if isinstance(end_time, str) else end_time,
                        location=event.get('location'),
                        is_all_day=True if 'date' in start else False,
                        google_event_id=event['id']
                    )
                    db.add(cal_event)
                    imported_count += 1
        
        db.commit()
        sync.last_synced_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"Synced {imported_count} events from Google Calendar")
        return {
            "status": "synced",
            "events_imported": imported_count,
            "last_synced": sync.last_synced_at.isoformat()
        }
    except Exception as e:
        logger.error(f"Error syncing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync-status")
def get_sync_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    '''Get Google Calendar sync status'''
    sync = db.query(GoogleCalendarSync).filter(GoogleCalendarSync.user_id == current_user.id).first()
    
    if not sync:
        return {"connected": False}
    
    return {
        "connected": True,
        "calendar_name": sync.google_calendar_id,
        "sync_enabled": sync.sync_enabled,
        "last_synced": sync.last_synced_at.isoformat() if sync.last_synced_at else None
    }


@router.post("/disconnect")
def disconnect_google_calendar(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    '''Disconnect Google Calendar'''
    sync = db.query(GoogleCalendarSync).filter(GoogleCalendarSync.user_id == current_user.id).first()
    
    if sync:
        db.delete(sync)
        db.commit()
    
    logger.info(f"Google Calendar disconnected for user: {current_user.email}")
    return {"status": "disconnected"}
