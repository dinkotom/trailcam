import json
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
SCOPES = ['https://www.googleapis.com/auth/drive']

def get_drive_service():
    """Authenticates and returns the Drive service."""
    creds = None
    log = logging.getLogger("drive_ops")

    # Scopes are not passed for user credentials on purpose: the token is reused
    # with the scopes it was issued for, otherwise Google returns invalid_scope
    # on refresh.

    # 1. Try OAuth2 user token from the environment (ephemeral runners, e.g. CI)
    if Config.GOOGLE_TOKEN_JSON:
        try:
            creds = Credentials.from_authorized_user_info(
                json.loads(Config.GOOGLE_TOKEN_JSON))
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            log.info("Using OAuth2 token from GOOGLE_TOKEN_JSON.")
        except Exception as e:
            log.warning(f"Error loading GOOGLE_TOKEN_JSON: {e}")
            creds = None

    # 2. Try OAuth2 user token file (local runs)
    token_path = Config.GOOGLE_TOKEN_FILE
    if not creds and os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path)
            # Refresh if expired
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
        except Exception as e:
            log.warning(f"Error loading token.json: {e}")
            creds = None
            
    # 3. Fallback to Service Account (if no token)
    if not creds:
        sa_path = Config.GOOGLE_SA_FILE
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

def list_folder_checksums(service, folder_id):
    """
    Returns {md5Checksum: name} for the files already in a folder.

    Used to make uploads idempotent: the same photo is never uploaded twice, even
    if the processed-message history is empty (new host, lost or pruned state).
    """
    checksums = {}
    page_token = None
    while True:
        response = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            spaces='drive',
            fields='nextPageToken, files(name, md5Checksum)',
            pageSize=1000,
            pageToken=page_token,
        ).execute()
        for f in response.get('files', []):
            if f.get('md5Checksum'):
                checksums[f['md5Checksum']] = f['name']
        page_token = response.get('nextPageToken')
        if not page_token:
            return checksums


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
