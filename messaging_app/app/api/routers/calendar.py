from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.calendar import CalendarEvent, UserCalendarSettings
from app.api.schemas.calendar import (
    CalendarEventCreate,
    CalendarEventUpdate,
    CalendarEventPublic,
    CalendarSettingsPublic,
    GoogleCalendarSync
)
from app.dependencies import get_current_user
from app.utils.google_calendar import get_credentials_from_code, sync_google_events_to_db
from datetime import datetime


router = APIRouter()


@router.post("/events", response_model=CalendarEventPublic, status_code=201)
def create_event(
    event: CalendarEventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new calendar event."""
    if event.start_time >= event.end_time:
        raise HTTPException(status_code=400, detail="Start time must be before end time")
    
    new_event = CalendarEvent(
        user_id=current_user.id,
        title=event.title,
        description=event.description,
        start_time=event.start_time,
        end_time=event.end_time,
        location=event.location,
        is_all_day=event.is_all_day
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return new_event


@router.get("/events", response_model=list[CalendarEventPublic])
def get_my_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's calendar events."""
    events = db.query(CalendarEvent).filter(
        CalendarEvent.user_id == current_user.id
    ).order_by(CalendarEvent.start_time).all()
    return events


@router.get("/events/{user_id}", response_model=list[CalendarEventPublic])
def get_user_events(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get another user's calendar events (if their calendar is public)."""
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if their calendar is public
    settings = db.query(UserCalendarSettings).filter(
        UserCalendarSettings.user_id == user_id
    ).first()
    
    if not settings or not settings.is_public:
        raise HTTPException(status_code=403, detail="User's calendar is private")
    
    events = db.query(CalendarEvent).filter(
        CalendarEvent.user_id == user_id
    ).order_by(CalendarEvent.start_time).all()
    
    return events


@router.put("/events/{event_id}", response_model=CalendarEventPublic)
def update_event(
    event_id: str,
    event_update: CalendarEventUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a calendar event."""
    event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if event.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot update this event")
    
    # Update fields
    if event_update.title:
        event.title = event_update.title
    if event_update.description:
        event.description = event_update.description
    if event_update.start_time:
        event.start_time = event_update.start_time
    if event_update.end_time:
        event.end_time = event_update.end_time
    if event_update.location:
        event.location = event_update.location
    if event_update.is_all_day is not None:
        event.is_all_day = event_update.is_all_day
    
    db.commit()
    db.refresh(event)
    return event


@router.delete("/events/{event_id}", status_code=200)
def delete_event(
    event_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a calendar event."""
    event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if event.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot delete this event")
    
    db.delete(event)
    db.commit()
    return {"message": "Event deleted"}


@router.post("/settings/make-public", response_model=CalendarSettingsPublic)
def make_calendar_public(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Make your calendar public."""
    settings = db.query(UserCalendarSettings).filter(
        UserCalendarSettings.user_id == current_user.id
    ).first()
    
    if not settings:
        settings = UserCalendarSettings(user_id=current_user.id, is_public=True)
        db.add(settings)
    else:
        settings.is_public = True
    
    db.commit()
    db.refresh(settings)
    return settings


@router.post("/settings/make-private", response_model=CalendarSettingsPublic)
def make_calendar_private(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Make your calendar private."""
    settings = db.query(UserCalendarSettings).filter(
        UserCalendarSettings.user_id == current_user.id
    ).first()
    
    if not settings:
        settings = UserCalendarSettings(user_id=current_user.id, is_public=False)
        db.add(settings)
    else:
        settings.is_public = False
    
    db.commit()
    db.refresh(settings)
    return settings


@router.post("/google/sync")
def sync_google_calendar(
    sync_data: GoogleCalendarSync,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Sync events from Google Calendar."""
    try:
        # Get credentials from authorization code
        credentials = get_credentials_from_code(sync_data.authorization_code)
        
        # Save credentials to database
        settings = db.query(UserCalendarSettings).filter(
            UserCalendarSettings.user_id == current_user.id
        ).first()
        
        if not settings:
            settings = UserCalendarSettings(
                user_id=current_user.id,
                google_access_token=credentials['access_token'],
                google_refresh_token=credentials['refresh_token']
            )
            db.add(settings)
        else:
            settings.google_access_token = credentials['access_token']
            settings.google_refresh_token = credentials['refresh_token']
        
        db.commit()
        
        # Sync events
        sync_google_events_to_db(
            current_user.id,
            credentials['access_token'],
            db
        )
        
        return {"message": "Google Calendar synced successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync calendar: {str(e)}")
