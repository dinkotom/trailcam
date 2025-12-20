import os
import io
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from src.config import Config

# Scopes
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_drive_service():
    """Authenticates and returns the Drive service."""
    creds = None
    log = logging.getLogger("drive_ops")
    
    # 1. Try OAuth2 User Token (Preferred)
    token_path = 'token.json'  # or Config.OAUTH_TOKEN_FILE
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            # Refresh if expired
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
        except Exception as e:
            log.warning(f"Error loading token.json: {e}")
            creds = None
            
    # 2. Fallback to Service Account (if no token)
    if not creds:
        sa_path = getattr(Config, 'GOOGLE_SERVICE_ACCOUNT_FILE', 'service_account.json')
        if os.path.exists(sa_path):
            log.info("Using Service Account credentials.")
            creds = service_account.Credentials.from_service_account_file(
                sa_path, scopes=SCOPES)
    
    if not creds:
        raise ValueError("No valid credentials found (token.json or service_account.json)")

    return build('drive', 'v3', credentials=creds)

def ensure_folder(service, folder_name, parent_id=None):
    """
    Checks if folder exists inside parent_id. 
    If not, creates it.
    Returns folder_id.
    """
    log = logging.getLogger("drive_ops")
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
        
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = results.get('files', [])
    
    if files:
        # Folder exists
        return files[0]['id']
    else:
        # Create folder
        log.info(f"Creating folder '{folder_name}'...")
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]
            
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')

def upload_file(service, file_path, file_name, folder_id):
    """Uploads a file to specific folder."""
    log = logging.getLogger("drive_ops")
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_path, mimetype='image/jpeg', resumable=True)
    
    # log.debug(f"Starting upload: {file_name}")
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    # log.debug(f"File ID: {file.get('id')}")
    return file.get('id')
