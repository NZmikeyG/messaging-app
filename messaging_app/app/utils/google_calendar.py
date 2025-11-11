from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']


class GoogleCalendarIntegration:
    '''Handle Google Calendar OAuth2 and sync'''
    
    def __init__(self):
        self.client_id = os.getenv('GOOGLE_CALENDAR_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CALENDAR_CLIENT_SECRET')
        self.redirect_uri = os.getenv('GOOGLE_CALENDAR_REDIRECT_URI', 'http://localhost:8000/api/calendar/google/callback')
    
    
    def get_auth_url(self, state: str):
        '''Get Google OAuth2 authorization URL'''
        flow = InstalledAppFlow.from_client_secrets_file(
            'google_credentials.json',
            SCOPES
        )
        auth_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
        return auth_url, state
    
    
    def exchange_code_for_tokens(self, auth_code: str):
        '''Exchange authorization code for access token'''
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                'google_credentials.json',
                SCOPES,
                redirect_uri=self.redirect_uri
            )
            credentials = flow.fetch_token(code=auth_code)
            
            return {
                'access_token': credentials.get('access_token'),
                'refresh_token': credentials.get('refresh_token'),
                'expires_in': credentials.get('expires_in')
            }
        except Exception as e:
            logger.error(f'Error exchanging code: {str(e)}')
            raise
    
    
    def refresh_access_token(self, refresh_token: str):
        '''Refresh expired access token'''
        try:
            # Would need to implement proper refresh logic
            # This is a simplified example
            logger.info(f'Refreshing token...')
            return refresh_token
        except Exception as e:
            logger.error(f'Error refreshing token: {str(e)}')
            raise
    
    
    def get_calendar_list(self, access_token: str):
        '''Get list of user's Google Calendars'''
        try:
            service = build('calendar', 'v3', credentials=access_token)
            calendars = service.calendarList().list().execute()
            return calendars.get('items', [])
        except HttpError as e:
            logger.error(f'Google API Error: {str(e)}')
            raise
    
    
    def sync_calendar_events(self, access_token: str, google_calendar_id: str, start_time: datetime = None):
        '''Sync events from Google Calendar'''
        try:
            service = build('calendar', 'v3', credentials=access_token)
            
            events_result = service.events().list(
                calendarId=google_calendar_id,
                maxResults=100,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            return events_result.get('items', [])
        except HttpError as e:
            logger.error(f'Error syncing events: {str(e)}')
            raise
    
    
    def create_event_on_google(self, access_token: str, google_calendar_id: str, event_data: dict):
        '''Create event on Google Calendar'''
        try:
            service = build('calendar', 'v3', credentials=access_token)
            
            event = service.events().insert(
                calendarId=google_calendar_id,
                body=event_data
            ).execute()
            
            return event
        except HttpError as e:
            logger.error(f'Error creating event: {str(e)}')
            raise


google_calendar = GoogleCalendarIntegration()
