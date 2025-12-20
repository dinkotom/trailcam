import os
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from .config import Config

SCOPES = ['https://www.googleapis.com/auth/drive']

from google.oauth2.credentials import Credentials

def get_drive_service():
    """Authenticate and return the Drive service."""
    creds = None
    
    # Priority 1: User OAuth Token (Solves Quota Issues)
    token_path = 'token.json'  # Assumes root or relative
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # Priority 2: Service Account (Server-to-Server, but limits quota on personal accounts)
    elif os.path.exists(Config.GOOGLE_SA_FILE):
        creds = service_account.Credentials.from_service_account_file(
            Config.GOOGLE_SA_FILE, scopes=SCOPES)
            
    if creds:
        return build('drive', 'v3', credentials=creds)
    else:
        raise FileNotFoundError("No valid 'token.json' or Service Account file found.")

def find_folder(service, name, parent_id=None):
    """Finds a folder by name within a parent."""
    query = f"mimeType='application/vnd.google-apps.folder' and name='{name}' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = results.get('files', [])
    if files:
        return files[0]['id']
    return None

def create_folder(service, name, parent_id=None):
    """Creates a folder."""
    file_metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        file_metadata['parents'] = [parent_id]
        
    file = service.files().create(body=file_metadata, fields='id').execute()
    return file.get('id')

def ensure_folder(service, name, parent_id=None):
    """Get folder ID, create if not processing."""
    folder_id = find_folder(service, name, parent_id)
    if not folder_id:
        folder_id = create_folder(service, name, parent_id)
    return folder_id

def upload_file(service, local_path, filename, folder_id):
    """Uploads a file to the specified folder."""
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
    media = MediaFileUpload(local_path, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')
