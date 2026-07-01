import os
import sys
import json
import logging
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io

logger = logging.getLogger("GoogleAPIHelper")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_credentials():
    # Try multiple paths for credentials (user oauth prioritized over service accounts)
    possible_paths = [
        os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE"),
        os.environ.get("GS_TOKEN"), # GHA uses GS_TOKEN for credentials content or path
        "/media/vpsg16gb/Workspace/goctoiphapluat/user_oauth2.json",
        "/media/vpsg16gb/Workspace/lelehoctiengtrung/Pipeline_lelehoctiengtrung/gitignore/user_oauth2.json",
        "/media/vpsg16gb/Workspace/goctoiphapluat/service_account.json",
        "/media/vpsg16gb/Workspace/lelehoctiengtrung/Pipeline_lelehoctiengtrung/gitignore/service_account.json"
    ]
    
    for path in possible_paths:
        if path and os.path.exists(path):
            try:
                with open(path, "r") as f:
                    info = json.load(f)
                if "private_key" in info:
                    return Credentials.from_service_account_info(info, scopes=SCOPES)
                elif "refresh_token" in info:
                    from google.oauth2.credentials import Credentials as UserCredentials
                    return UserCredentials(
                        token=None,
                        refresh_token=info["refresh_token"],
                        token_uri=info.get("token_uri", "https://oauth2.googleapis.com/token"),
                        client_id=info["client_id"],
                        client_secret=info["client_secret"],
                        scopes=SCOPES
                    )
            except Exception as e:
                logger.error(f"Error loading credentials from {path}: {e}")
                
    # If a path was passed but it was a JSON string itself
    for env_var in ["GS_TOKEN", "GOOGLE_SERVICE_ACCOUNT_JSON"]:
        val = os.environ.get(env_var)
        if val and val.strip().startswith("{"):
            try:
                info = json.loads(val)
                if "private_key" in info:
                    return Credentials.from_service_account_info(info, scopes=SCOPES)
                elif "refresh_token" in info:
                    from google.oauth2.credentials import Credentials as UserCredentials
                    return UserCredentials(
                        token=None,
                        refresh_token=info["refresh_token"],
                        token_uri=info.get("token_uri", "https://oauth2.googleapis.com/token"),
                        client_id=info["client_id"],
                        client_secret=info["client_secret"],
                        scopes=SCOPES
                    )
            except Exception as e:
                logger.error(f"Error parsing JSON credentials from env {env_var}: {e}")
                
    raise FileNotFoundError("Could not find valid service account or user oauth credentials in env or standard paths.")

def get_gspread_client():
    creds = get_credentials()
    return gspread.authorize(creds)

def get_drive_service():
    creds = get_credentials()
    return build('drive', 'v3', credentials=creds)

def create_drive_folder(folder_name, parent_id=None):
    """Creates a folder in Google Drive and returns (folder_id, folder_url)"""
    service = get_drive_service()
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id] if parent_id else []
    }
    try:
        folder = service.files().create(body=file_metadata, fields='id').execute()
        folder_id = folder.get('id')
        folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
        logger.info(f"Created folder '{folder_name}' with ID: {folder_id}")
        return folder_id, folder_url
    except Exception as e:
        logger.error(f"Failed to create Google Drive folder: {e}")
        raise

def upload_to_gdoc(local_path, doc_name, folder_id):
    """Uploads a local text file to Google Drive and converts it to a Google Doc."""
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"Local file not found: {local_path}")
        
    service = get_drive_service()
    file_metadata = {
        'name': doc_name,
        'mimeType': 'application/vnd.google-apps.document', # Triggers conversion to Google Doc
        'parents': [folder_id] if folder_id else []
    }
    
    media = MediaFileUpload(local_path, mimetype='text/plain', resumable=True)
    try:
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        doc_id = file.get('id')
        doc_url = file.get('webViewLink')
        logger.info(f"Uploaded and converted '{doc_name}'. Doc URL: {doc_url}")
        return doc_id, doc_url
    except Exception as e:
        logger.error(f"Failed to upload doc to Google Drive: {e}")
        raise

def download_gdoc_as_text(file_id, local_path):
    """Downloads a Google Doc as plain text."""
    service = get_drive_service()
    try:
        request = service.files().export_media(fileId=file_id, mimeType='text/plain')
        fh = io.FileIO(local_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        logger.info(f"Downloaded Google Doc ID '{file_id}' as text to '{local_path}'")
        return True
    except Exception as e:
        logger.error(f"Failed to download Google Doc: {e}")
        raise

def create_sheet_in_folder(doc_name, folder_id):
    """Creates a new Google Sheet inside a Google Drive folder."""
    service = get_drive_service()
    file_metadata = {
        'name': doc_name,
        'mimeType': 'application/vnd.google-apps.spreadsheet',
        'parents': [folder_id] if folder_id else []
    }
    try:
        file = service.files().create(
            body=file_metadata,
            fields='id, webViewLink'
        ).execute()
        sheet_id = file.get('id')
        sheet_url = file.get('webViewLink')
        logger.info(f"Created independent Google Sheet '{doc_name}' in folder. URL: {sheet_url}")
        return sheet_id, sheet_url
    except Exception as e:
        logger.error(f"Failed to create Google Sheet in folder: {e}")
        raise

