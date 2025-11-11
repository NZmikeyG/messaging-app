from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List
from app.database import get_db
from app.models.calendar import (
    Calendar, CalendarEvent, EventReminder, EventInvite, RecurringEventRule, 
    EventNotification, TeamCalendarView, CalendarTag
)
from app.models.user import User
from app.dependencies import get_current_user
import logging
from icalendar import Calendar as ICalCalendar
from icalendar import Event as ICalEvent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/calendar/advanced", tags=["calendar-advanced"])


# ============ REMINDERS ============

@router.post("/{event_id}/reminders")
def create_reminder(event_id: str, minutes_before: int = 15, reminder_type: str = "email", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    '''Create a reminder for an event'''
    event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    reminder = EventReminder(
        event_id=event_id,
        remind_at=event.start_time - timedelta(minutes=minutes_before),
        reminder_type=reminder_type
    )
    db.add(reminder)
    db.commit()
    logger.info(f"Reminder created for event {event_id}")
    return {"id": str(reminder.id), "remind_at": reminder.remind_at.isoformat()}


@router.get("/{event_id}/reminders", response_model=List[dict])
def get_reminders(event_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    '''Get reminders for an event'''
    reminders = db.query(EventReminder).filter(EventReminder.event_id == event_id).all()
    return [{"id": str(r.id), "remind_at": r.remind_at.isoformat(), "type": r.reminder_type, "sent": r.is_sent} for r in reminders]


@router.delete("/reminders/{reminder_id}", status_code=204)
def delete_reminder(reminder_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    '''Delete a reminder'''
    reminder = db.query(EventReminder).filter(EventReminder.id == reminder_id).first()
    if reminder:
        db.delete(reminder)
        db.commit()


# ============ INVITES & RSVP ============

@router.post("/{event_id}/invite/{user_id}")
def invite_to_event(event_id: str, user_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    '''Invite user to event'''
    event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    existing = db.query(EventInvite).filter(
        EventInvite.event_id == event_id,
        EventInvite.invitee_id == user_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="User already invited")
    
    invite = EventInvite(
        event_id=event_id,
        invitee_id=user_id,
        status="pending"
    )
    db.add(invite)
    
    # Create notification
    notification = EventNotification(
        user_id=user_id,
        event_id=event_id,
        notification_type="invite",
        message=f"You've been invited to: {event.title}"
    )
    db.add(notification)
    db.commit()
    
    logger.info(f"Invite sent for event {event_id} to user {user_id}")
    return {"status": "invited"}


@router.get("/{event_id}/invites", response_model=List[dict])
def get_event_invites(event_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    '''Get invites for an event'''
    invites = db.query(EventInvite).filter(EventInvite.event_id == event_id).all()
    return [{
        "id": str(i.id),
        "invitee_id": str(i.invitee_id),
        "status": i.status,
        "responded_at": i.response_at.isoformat() if i.response_at else None
    } for i in invites]


@router.post("/invites/{invite_id}/accept")
def accept_invite(invite_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    '''Accept event invite'''
    invite = db.query(EventInvite).filter(EventInvite.id == invite_id).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    
    invite.status = "accepted"
    invite.response_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"Invite {invite_id} accepted")
    return {"status": "accepted"}


@router.post("/invites/{invite_id}/decline")
def decline_invite(invite_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    '''Decline event invite'''
    invite = db.query(EventInvite).filter(EventInvite.id == invite_id).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    
    invite.status = "declined"
    invite.response_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"Invite {invite_id} declined")
    return {"status": "declined"}


# ============ RECURRING EVENTS ============

@router.post("/{event_id}/recurring")
def set_recurrence(event_id: str, frequency: str, interval: int = 1, end_date: str = None, days_of_week: str = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    '''Set event recurrence'''
    event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if frequency not in ["daily", "weekly", "monthly", "yearly"]:
        raise HTTPException(status_code=400, detail="Invalid frequency")
    
    rule = RecurringEventRule(
        original_event_id=event_id,
        frequency=frequency,
        interval=interval,
        end_date=datetime.fromisoformat(end_date) if end_date else None,
        days_of_week=days_of_week
    )
    db.add(rule)
    db.commit()
    
    logger.info(f"Recurrence set for event {event_id}: {frequency}")
    return {"id": str(rule.id), "frequency": frequency}


@router.get("/{event_id}/recurring")
def get_recurrence(event_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    '''Get recurrence rule for event'''
    rule = db.query(RecurringEventRule).filter(RecurringEventRule.original_event_id == event_id).first()
    if not rule:
        return {"recurring": False}
    
    return {
        "recurring": True,
        "frequency": rule.frequency,
        "interval": rule.interval,
        "end_date": rule.end_date.isoformat() if rule.end_date else None,
        "days_of_week": rule.days_of_week
    }


# ============ TAGS ============

@router.post("/{calendar_id}/tags")
def create_tag(calendar_id: str, name: str, color: str = "#808080", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    '''Create calendar tag/category'''
    calendar = db.query(Calendar).filter(Calendar.id == calendar_id).first()
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendar not found")
    
    tag = CalendarTag(
        calendar_id=calendar_id,
        name=name,
        color=color
    )
    db.add(tag)
    db.commit()
    return {"id": str(tag.id), "name": tag.name, "color": tag.color}


@router.get("/{calendar_id}/tags", response_model=List[dict])
def get_tags(calendar_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    '''Get calendar tags'''
    tags = db.query(CalendarTag).filter(CalendarTag.calendar_id == calendar_id).all()
    return [{"id": str(t.id), "name": t.name, "color": t.color} for t in tags]


# ============ NOTIFICATIONS ============

@router.get("/notifications", response_model=List[dict])
def get_notifications(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    '''Get user's calendar notifications'''
    notifications = db.query(EventNotification).filter(
        EventNotification.user_id == current_user.id,
        EventNotification.is_read == False
    ).all()
    
    return [{
        "id": str(n.id),
        "type": n.notification_type,
        "message": n.message,
        "event_id": str(n.event_id),
        "created_at": n.created_at.isoformat()
    } for n in notifications]


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    '''Mark notification as read'''
    notification = db.query(EventNotification).filter(EventNotification.id == notification_id).first()
    if notification:
        notification.is_read = True
        db.commit()
    
    return {"status": "read"}


# ============ TEAM CALENDAR VIEWS ============

@router.post("/{channel_id}/team-view")
def create_team_calendar_view(channel_id: str, name: str, description: str = None, included_calendars: dict = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    '''Create team calendar view for channel'''
    view = TeamCalendarView(
        channel_id=channel_id,
        name=name,
        description=description,
        included_calendars=included_calendars or {},
        created_by=current_user.id
    )
    db.add(view)
    db.commit()
    logger.info(f"Team calendar view created: {name}")
    return {"id": str(view.id), "name": view.name}


@router.get("/{channel_id}/team-views", response_model=List[dict])
def get_team_calendar_views(channel_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    '''Get team calendar views for channel'''
    views = db.query(TeamCalendarView).filter(TeamCalendarView.channel_id == channel_id).all()
    return [{"id": str(v.id), "name": v.name, "description": v.description} for v in views]


# ============ ICAL EXPORT ============

@router.get("/{calendar_id}/export/ical")
def export_to_ical(calendar_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    '''Export calendar to iCalendar format'''
    calendar = db.query(Calendar).filter(Calendar.id == calendar_id).first()
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendar not found")
    
    # Create iCal calendar
    ical = ICalCalendar()
    ical.add('prodid', '-//My Calendar//EN')
    ical.add('version', '2.0')
    ical.add('name', calendar.name)
    
    # Add events
    events = db.query(CalendarEvent).filter(CalendarEvent.calendar_id == calendar_id).all()
    
    for event in events:
        ical_event = ICalEvent()
        ical_event.add('summary', event.title)
        ical_event.add('description', event.description or '')
        ical_event.add('dtstart', event.start_time)
        ical_event.add('dtend', event.end_time)
        ical_event.add('location', event.location or '')
        ical_event.add('uid', str(event.id))
        ical_event.add('dtstamp', datetime.utcnow())
        ical.add_component(ical_event)
    
    logger.info(f"Calendar {calendar_id} exported to iCal")
    return {
        "status": "exported",
        "ical": ical.to_ical().decode('utf-8'),
        "events_count": len(events)
    }
