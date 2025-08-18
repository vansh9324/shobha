from __future__ import print_function
import os
import io
import json
import datetime
from typing import Optional

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

SCOPES = ['https://www.googleapis.com/auth/drive.file']

class DriveUploader:
    def __init__(self):
        if not GOOGLE_AVAILABLE:
            raise RuntimeError("Google API libraries not available")
            
        self.main_folder_id = "1doyiFBYxHfdbLmqu2seRZJMbPH2940_z"
        
        try:
            self.service = self._authenticate()
            print(f"✅ Google Drive connected to folder: {self.main_folder_id}")
        except Exception as e:
            print(f"❌ Google Drive authentication failed: {e}")
            raise RuntimeError(f"Drive authentication failed: {e}")

    def _authenticate(self):
        client_info_str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        if not client_info_str:
            raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS missing")

        refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN", "").strip()
        if not refresh_token:
            raise RuntimeError("GOOGLE_REFRESH_TOKEN missing")

        try:
            client_info = json.loads(client_info_str)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid GOOGLE_APPLICATION_CREDENTIALS JSON: {e}")

        if "installed" not in client_info:
            raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS must contain 'installed' client")

        installed = client_info["installed"]
        client_id = installed.get("client_id")
        client_secret = installed.get("client_secret")
        token_uri = installed.get("token_uri", "https://oauth2.googleapis.com/token")

        if not client_id or not client_secret:
            raise RuntimeError("Missing client_id/client_secret")

        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES,
        )

        try:
            creds.refresh(Request())
        except Exception as e:
            raise RuntimeError(f"Token refresh failed: {e}")

        service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        return service

    def get_or_create_folder(self, folder_name: str, parent_id: str) -> str:
        query = (
            f"name='{folder_name}' and "
            f"mimeType='application/vnd.google-apps.folder' and "
            f"'{parent_id}' in parents and trashed = false"
        )
        
        results = self.service.files().list(q=query, fields="files(id,name)").execute()
        folders = results.get('files', [])
        
        if folders:
            print(f"📁 Found folder: {folder_name}")
            return folders[0]['id']
        else:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            folder = self.service.files().create(body=folder_metadata, fields="id,name").execute()
            print(f"📁 Created folder: {folder_name}")
            return folder.get('id')

    def upload_image(self, image_bytes: io.BytesIO, filename: str, catalog: Optional[str] = None) -> str:
        try:
            parent_id = self.main_folder_id
            
            if catalog:
                catalog_folder_id = self.get_or_create_folder(catalog, parent_id)
            else:
                catalog_folder_id = parent_id

            # Handle filename conflicts
            dup_query = f"name='{filename}' and '{catalog_folder_id}' in parents and trashed = false"
            existing = self.service.files().list(q=dup_query, fields="files(id,name)").execute().get('files', [])
            
            if existing:
                ts = datetime.datetime.now().strftime("%H%M%S")
                name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
                filename = f"{name}_{ts}.{ext}" if ext else f"{name}_{ts}"
                print(f"⚠️ Renamed to avoid conflict: {filename}")

            image_bytes.seek(0)
            media = MediaIoBaseUpload(image_bytes, mimetype='image/jpeg', resumable=True)
            file_metadata = {'name': filename, 'parents': [catalog_folder_id]}
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink'
            ).execute()
            
            print(f"✅ Uploaded: {filename}")
            return file.get('webViewLink')
            
        except Exception as e:
            print(f"❌ Upload failed: {e}")
            raise e
