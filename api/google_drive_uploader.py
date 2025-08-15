from __future__ import print_function
import os
import io
import json
import datetime
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Same scope as before
SCOPES = ['https://www.googleapis.com/auth/drive.file']

class DriveUploader:
    def __init__(self):
        # Use your existing main folder ID from original code
        self.main_folder_id = "1doyiFBYxHfdbLmqu2seRZJMbPH2940_z"

        # Build service using client credentials + refresh token from env
        self.service = self._authenticate()

        print(f"✅ Connected to Shobha Sarees folder: {self.main_folder_id}")

    def _authenticate(self):
        """
        Non-interactive auth for serverless:
        - Reads Installed OAuth client JSON from GOOGLE_APPLICATION_CREDENTIALS (env).
        - Reads GOOGLE_REFRESH_TOKEN (env).
        - Builds google.oauth2.credentials.Credentials directly and refreshes if needed.
        """
        client_info_str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        if not client_info_str:
            raise RuntimeError("Missing GOOGLE_APPLICATION_CREDENTIALS env var.")

        refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN", "").strip()
        if not refresh_token:
            raise RuntimeError("Missing GOOGLE_REFRESH_TOKEN env var. Generate it once locally with the same client and scope.")

        try:
            client_info = json.loads(client_info_str)
        except Exception as e:
            raise RuntimeError(f"GOOGLE_APPLICATION_CREDENTIALS is not valid JSON: {e}")

        # Extract client_id and client_secret from the 'installed' block
        if "installed" not in client_info:
            raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS must contain an 'installed' client (OAuth client).")
        installed = client_info["installed"]
        client_id = installed.get("client_id")
        client_secret = installed.get("client_secret")
        token_uri = installed.get("token_uri", "https://oauth2.googleapis.com/token")

        if not client_id or not client_secret:
            raise RuntimeError("Missing client_id/client_secret in GOOGLE_APPLICATION_CREDENTIALS.")

        # Build non-interactive credentials with a refresh token
        creds = Credentials(
            token=None,  # access token will be fetched via refresh
            refresh_token=refresh_token,
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES,
        )

        # Refresh immediately to ensure we have a valid access token
        creds.refresh(Request())

        # Disable discovery cache (no disk writes)
        service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        return service

    def get_or_create_folder(self, folder_name: str, parent_id: str) -> str:
        """Get existing folder or create new one in specific parent."""
        query = (
            f"name='{folder_name}' and "
            f"mimeType='application/vnd.google-apps.folder' and "
            f"'{parent_id}' in parents and trashed = false"
        )

        results = self.service.files().list(q=query, fields="files(id,name)").execute()
        folders = results.get('files', [])

        if folders:
            print(f"📁 Found existing folder: {folder_name}")
            return folders[0]['id']
        else:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            folder = self.service.files().create(body=folder_metadata, fields="id,name").execute()
            print(f"📁 Created new folder: {folder_name}")
            return folder.get('id')

    def upload_image(self, image_bytes: io.BytesIO, filename: str, catalog: Optional[str] = None) -> str:
        """
        Upload to specific catalog folder within Shobha Sarees
        Structure: Shobha Sarees/{catalog}/{filename}
        """
        try:
            # Resolve target parent
            parent_id = self.main_folder_id
            if catalog:
                catalog_folder_id = self.get_or_create_folder(catalog, parent_id)
            else:
                catalog_folder_id = parent_id

            # Handle duplicates by renaming with timestamp
            dup_query = f"name='{filename}' and '{catalog_folder_id}' in parents and trashed = false"
            existing_files = self.service.files().list(q=dup_query, fields="files(id,name)").execute().get('files', [])
            if existing_files:
                ts = datetime.datetime.now().strftime("%H%M%S")
                parts = filename.rsplit('.', 1)
                if len(parts) == 2:
                    filename = f"{parts[0]}_{ts}.{parts[1]}"
                else:
                    filename = f"{filename}_{ts}"
                print(f"⚠️ File exists, renamed to: {filename}")

            image_bytes.seek(0)
            media = MediaIoBaseUpload(image_bytes, mimetype='image/jpeg', resumable=True)
            file_metadata = {'name': filename, 'parents': [catalog_folder_id]}

            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink'
            ).execute()

            print(f"✅ Uploaded: {filename} to Shobha Sarees/{catalog or ''}")
            return file.get('webViewLink')

        except Exception as e:
            print(f"❌ Upload error: {str(e)}")
            raise e
