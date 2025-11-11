from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
import os
import io
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
SCOPES = ['https://www.googleapis.com/auth/drive']

class GoogleDriveIntegration:
    def __init__(self):
        self.credentials_file = os.getenv('GOOGLE_DRIVE_CREDENTIALS_FILE', 'google_credentials.json')
    
    def get_auth_url(self, state: str):
        try:
            flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
            auth_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
            return auth_url, state
        except Exception as e:
            logger.error(f'Error getting auth URL: {str(e)}')
            raise
    
    def exchange_code_for_tokens(self, auth_code: str):
        try:
            flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
            credentials = flow.fetch_token(code=auth_code)
            return {'access_token': credentials.get('access_token'), 'refresh_token': credentials.get('refresh_token')}
        except Exception as e:
            logger.error(f'Error exchanging code: {str(e)}')
            raise
    
    def create_team_folder(self, access_token: str, folder_name: str = "Team Drive"):
        try:
            service = self._get_service(access_token)
            file_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
            folder = service.files().create(body=file_metadata, fields='id, webViewLink').execute()
            logger.info(f'Created team folder: {folder_name}')
            return folder
        except HttpError as e:
            logger.error(f'Error creating folder: {str(e)}')
            raise
    
    def upload_file(self, access_token: str, file_path: str, file_name: str, folder_id: str):
        try:
            service = self._get_service(access_token)
            file_metadata = {'name': file_name, 'parents': [folder_id]}
            media = MediaFileUpload(file_path, resumable=True)
            file = service.files().create(body=file_metadata, media_body=media, 
                fields='id, name, mimeType, size, webViewLink, createdTime').execute()
            logger.info(f'Uploaded file: {file_name}')
            return file
        except HttpError as e:
            logger.error(f'Error uploading file: {str(e)}')
            raise
    
    def list_files(self, access_token: str, folder_id: str, page_size: int = 100):
        try:
            service = self._get_service(access_token)
            query = f"'{folder_id}' in parents and trashed=false"
            results = service.files().list(q=query, spaces='drive', 
                fields='files(id, name, mimeType, size, webViewLink, createdTime)', 
                pageSize=page_size, orderBy='modifiedTime desc').execute()
            return results.get('files', [])
        except HttpError as e:
            logger.error(f'Error listing files: {str(e)}')
            raise
    
    def download_file(self, access_token: str, file_id: str, file_path: str):
        try:
            service = self._get_service(access_token)
            request = service.files().get_media(fileId=file_id)
            file = io.BytesIO()
            downloader = MediaIoBaseDownload(file, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            with open(file_path, 'wb') as f:
                f.write(file.getvalue())
            logger.info(f'Downloaded file: {file_id}')
            return file_path
        except HttpError as e:
            logger.error(f'Error downloading file: {str(e)}')
            raise
    
    def delete_file(self, access_token: str, file_id: str):
        try:
            service = self._get_service(access_token)
            service.files().delete(fileId=file_id).execute()
            logger.info(f'Deleted file: {file_id}')
            return True
        except HttpError as e:
            logger.error(f'Error deleting file: {str(e)}')
            raise
    
    def share_file(self, access_token: str, file_id: str, email: str, role: str = 'reader'):
        try:
            service = self._get_service(access_token)
            permission = {'type': 'user', 'role': role, 'emailAddress': email}
            service.permissions().create(fileId=file_id, body=permission, fields='id').execute()
            logger.info(f'Shared file {file_id} with {email}')
            return True
        except HttpError as e:
            logger.error(f'Error sharing file: {str(e)}')
            raise
    
    def _get_service(self, access_token: str):
        from google.oauth2.credentials import Credentials
        credentials = Credentials(token=access_token)
        return build('drive', 'v3', credentials=credentials)

google_drive = GoogleDriveIntegration()
