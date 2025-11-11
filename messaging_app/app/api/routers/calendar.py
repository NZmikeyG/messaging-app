from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.calendar import Calendar, CalendarEvent, CalendarMember, CalendarSubscription, GoogleCalendarSync
from app.models.user import User
from app.dependencies import get_current_user
from app.api.schemas.calendar import CalendarEventCreate, CalendarEventPublic, CalendarEventUpdate
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/calendars", tags=["calendars"])


@router.get("/", response_model=List[CalendarEventPublic])
def get_events(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get user's calendar events."""
    events = db.query(CalendarEvent).filter(CalendarEvent.created_by == current_user.id).all()
    return events


@router.post("/events", response_model=CalendarEventPublic, status_code=201)
def create_event(event: CalendarEventCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Create a new calendar event."""
    new_event = CalendarEvent(
        title=event.title,
        description=event.description,
        start_time=event.start_time,
        end_time=event.end_time,
        location=event.location,
        is_all_day=event.is_all_day,
        created_by=current_user.id,
        calendar_id=None
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    logger.info(f"Event created: {event.title} by {current_user.email}")
    return new_event


@router.get("/events/{event_id}", response_model=CalendarEventPublic)
def get_event(event_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get a specific calendar event."""
    event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.put("/events/{event_id}", response_model=CalendarEventPublic)
def update_event(event_id: str, event: CalendarEventUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Update a calendar event."""
    db_event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
    if db_event.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db_event.title = event.title
    db_event.description = event.description
    db_event.start_time = event.start_time
    db_event.end_time = event.end_time
    db_event.location = event.location
    db_event.is_all_day = event.is_all_day
    db.commit()
    db.refresh(db_event)
    logger.info(f"Event updated: {event_id}")
    return db_event


@router.delete("/events/{event_id}", status_code=204)
def delete_event(event_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Delete a calendar event."""
    event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db.delete(event)
    db.commit()
    logger.info(f"Event deleted: {event_id}")
