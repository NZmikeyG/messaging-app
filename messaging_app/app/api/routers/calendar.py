from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from app.database import get_db
from app.models.calendar import Calendar, CalendarEvent, CalendarMember, CalendarSubscription, GoogleCalendarSync
from app.models.user import User
from app.dependencies import get_current_user
from app.api.schemas.calendar import CalendarEventCreate, CalendarEventPublic, CalendarEventUpdate
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/calendars", tags=["calendars"])


# ============ CALENDAR MANAGEMENT ============

@router.post("/", status_code=201)
def create_calendar(name: str, description: str = None, color: str = "#3366cc", is_public: bool = False, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Create a new calendar."""
    new_calendar = Calendar(
        owner_id=current_user.id,
        name=name,
        description=description,
        color=color,
        is_public=is_public
    )
    db.add(new_calendar)
    db.commit()
    db.refresh(new_calendar)
    logger.info(f"Calendar created: {name} by {current_user.email}")
    return {"id": str(new_calendar.id), "name": new_calendar.name, "color": new_calendar.color}


@router.get("/", response_model=List[dict])
def get_calendars(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get user's calendars (owned + shared)."""
    # User's own calendars
    owned = db.query(Calendar).filter(Calendar.owner_id == current_user.id).all()
    
    # Shared calendars (via memberships or subscriptions)
    shared = db.query(Calendar).join(CalendarMember).filter(
        CalendarMember.user_id == current_user.id
    ).all()
    
    all_calendars = owned + shared
    return [{"id": str(c.id), "name": c.name, "color": c.color, "owner": str(c.owner_id)} for c in all_calendars]


@router.get("/{calendar_id}")
def get_calendar(calendar_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get calendar details."""
    calendar = db.query(Calendar).filter(Calendar.id == calendar_id).first()
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendar not found")
    
    # Check permission
    if calendar.owner_id != current_user.id:
        member = db.query(CalendarMember).filter(
            CalendarMember.calendar_id == calendar_id,
            CalendarMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    return {
        "id": str(calendar.id),
        "name": calendar.name,
        "description": calendar.description,
        "color": calendar.color,
        "owner": str(calendar.owner_id),
        "is_public": calendar.is_public,
        "members_count": len(calendar.members)
    }


@router.put("/{calendar_id}")
def update_calendar(calendar_id: str, name: str = None, description: str = None, color: str = None, is_public: bool = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Update calendar."""
    calendar = db.query(Calendar).filter(Calendar.id == calendar_id).first()
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendar not found")
    if calendar.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can update")
    
    if name:
        calendar.name = name
    if description:
        calendar.description = description
    if color:
        calendar.color = color
    if is_public is not None:
        calendar.is_public = is_public
    
    db.commit()
    logger.info(f"Calendar updated: {calendar_id}")
    return {"id": str(calendar.id), "name": calendar.name}


@router.delete("/{calendar_id}", status_code=204)
def delete_calendar(calendar_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Delete calendar."""
    calendar = db.query(Calendar).filter(Calendar.id == calendar_id).first()
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendar not found")
    if calendar.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can delete")
    
    db.delete(calendar)
    db.commit()
    logger.info(f"Calendar deleted: {calendar_id}")


# ============ SHARING & PERMISSIONS ============

@router.post("/{calendar_id}/members/{user_id}")
def add_calendar_member(calendar_id: str, user_id: str, permission: str = "view", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Add member to calendar with permission (view/edit/admin)."""
    calendar = db.query(Calendar).filter(Calendar.id == calendar_id).first()
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendar not found")
    if calendar.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can add members")
    
    if permission not in ["view", "edit", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid permission")
    
    existing = db.query(CalendarMember).filter(
        CalendarMember.calendar_id == calendar_id,
        CalendarMember.user_id == user_id
    ).first()
    
    if existing:
        existing.permission = permission
    else:
        member = CalendarMember(
            calendar_id=calendar_id,
            user_id=user_id,
            permission=permission
        )
        db.add(member)
    
    db.commit()
    logger.info(f"Member added to calendar: {calendar_id} - {user_id} ({permission})")
    return {"status": "ok", "permission": permission}


@router.get("/{calendar_id}/members", response_model=List[dict])
def get_calendar_members(calendar_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get calendar members."""
    calendar = db.query(Calendar).filter(Calendar.id == calendar_id).first()
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendar not found")
    
    members = db.query(CalendarMember).filter(CalendarMember.calendar_id == calendar_id).all()
    return [{"user_id": str(m.user_id), "permission": m.permission} for m in members]


@router.delete("/{calendar_id}/members/{user_id}", status_code=204)
def remove_calendar_member(calendar_id: str, user_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Remove member from calendar."""
    calendar = db.query(Calendar).filter(Calendar.id == calendar_id).first()
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendar not found")
    if calendar.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only owner can remove members")
    
    member = db.query(CalendarMember).filter(
        CalendarMember.calendar_id == calendar_id,
        CalendarMember.user_id == user_id
    ).first()
    
    if member:
        db.delete(member)
        db.commit()
    
    logger.info(f"Member removed from calendar: {calendar_id} - {user_id}")


# ============ CALENDAR VISIBILITY/SUBSCRIPTIONS ============

@router.post("/{calendar_id}/subscribe")
def subscribe_calendar(calendar_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Subscribe to a calendar (show in user's view)."""
    calendar = db.query(Calendar).filter(Calendar.id == calendar_id).first()
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendar not found")
    
    existing = db.query(CalendarSubscription).filter(
        CalendarSubscription.calendar_id == calendar_id,
        CalendarSubscription.user_id == current_user.id
    ).first()
    
    if existing:
        existing.is_visible = True
    else:
        sub = CalendarSubscription(
            calendar_id=calendar_id,
            user_id=current_user.id,
            is_visible=True
        )
        db.add(sub)
    
    db.commit()
    logger.info(f"Calendar subscribed: {calendar_id}")
    return {"status": "subscribed"}


@router.post("/{calendar_id}/unsubscribe")
def unsubscribe_calendar(calendar_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Unsubscribe from calendar (hide from user's view)."""
    sub = db.query(CalendarSubscription).filter(
        CalendarSubscription.calendar_id == calendar_id,
        CalendarSubscription.user_id == current_user.id
    ).first()
    
    if sub:
        sub.is_visible = False
        db.commit()
    
    logger.info(f"Calendar unsubscribed: {calendar_id}")
    return {"status": "unsubscribed"}


@router.get("/{calendar_id}/visibility")
def get_calendar_visibility(calendar_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Check if calendar is visible to current user."""
    sub = db.query(CalendarSubscription).filter(
        CalendarSubscription.calendar_id == calendar_id,
        CalendarSubscription.user_id == current_user.id
    ).first()
    
    is_visible = sub.is_visible if sub else False
    return {"is_visible": is_visible}


# ============ EVENTS ============

@router.get("/{calendar_id}/events", response_model=List[dict])
def get_calendar_events(calendar_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get events for a calendar."""
    calendar = db.query(Calendar).filter(Calendar.id == calendar_id).first()
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendar not found")
    
    # Check permission
    if calendar.owner_id != current_user.id:
        member = db.query(CalendarMember).filter(
            CalendarMember.calendar_id == calendar_id,
            CalendarMember.user_id == current_user.id
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="Not authorized")
    
    events = db.query(CalendarEvent).filter(CalendarEvent.calendar_id == calendar_id).all()
    return [
        {
            "id": str(e.id),
            "title": e.title,
            "start_time": e.start_time.isoformat(),
            "end_time": e.end_time.isoformat(),
            "is_all_day": e.is_all_day
        } for e in events
    ]


@router.post("/{calendar_id}/events", status_code=201)
def create_calendar_event(calendar_id: str, event: CalendarEventCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Create event in calendar."""
    calendar = db.query(Calendar).filter(Calendar.id == calendar_id).first()
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendar not found")
    
    # Check permission to edit
    if calendar.owner_id != current_user.id:
        member = db.query(CalendarMember).filter(
            CalendarMember.calendar_id == calendar_id,
            CalendarMember.user_id == current_user.id,
            CalendarMember.permission.in_(["edit", "admin"])
        ).first()
        if not member:
            raise HTTPException(status_code=403, detail="No permission to edit")
    
    new_event = CalendarEvent(
        calendar_id=calendar_id,
        created_by=current_user.id,
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
    logger.info(f"Event created: {event.title} in calendar {calendar_id}")
    return {"id": str(new_event.id), "title": new_event.title}
