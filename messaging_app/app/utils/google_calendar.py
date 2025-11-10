from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
from datetime import datetime, timedelta


# Google OAuth Config
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
SCOPES = ['https://www.googleapis.com/auth/calendar']


def get_google_auth_url():
    """Get Google OAuth authorization URL."""
    flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=SCOPES,
        redirect_uri='http://localhost:8000/api/calendar/callback'
    )
    
    auth_url, state = flow.authorization_url(prompt='consent')
    return auth_url, state


def get_credentials_from_code(authorization_code: str):
    """Exchange authorization code for credentials."""
    flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=SCOPES,
        redirect_uri='http://localhost:8000/api/calendar/callback'
    )
    
    flow.fetch_token(code=authorization_code)
    credentials = flow.credentials
    
    return {
        'access_token': credentials.token,
        'refresh_token': credentials.refresh_token
    }


def get_google_events(access_token: str, days_ahead: int = 30):
    """Fetch events from Google Calendar."""
    try:
        credentials = Credentials(token=access_token)
        service = build('calendar', 'v3', credentials=credentials)
        
        now = datetime.utcnow().isoformat() + 'Z'
        future = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            timeMax=future,
            maxResults=100,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        return events_result.get('items', [])
    
    except HttpError as error:
        print(f'Google Calendar API error: {error}')
        return []


def sync_google_events_to_db(user_id: str, access_token: str, db):
    """Sync Google Calendar events to database."""
    from app.models.calendar import CalendarEvent
    
    google_events = get_google_events(access_token)
    
    for google_event in google_events:
        start_time = google_event['start'].get('dateTime') or google_event['start'].get('date')
        end_time = google_event['end'].get('dateTime') or google_event['end'].get('date')
        
        # Check if event already exists
        existing = db.query(CalendarEvent).filter(
            CalendarEvent.user_id == user_id,
            CalendarEvent.google_event_id == google_event['id']
        ).first()
        
        if existing:
            # Update existing event
            existing.title = google_event['summary']
            existing.description = google_event.get('description')
            existing.start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            existing.end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            existing.location = google_event.get('location')
        else:
            # Create new event
            new_event = CalendarEvent(
                user_id=user_id,
                title=google_event['summary'],
                description=google_event.get('description'),
                start_time=datetime.fromisoformat(start_time.replace('Z', '+00:00')),
                end_time=datetime.fromisoformat(end_time.replace('Z', '+00:00')),
                location=google_event.get('location'),
                google_event_id=google_event['id']
            )
            db.add(new_event)
    
    db.commit()
