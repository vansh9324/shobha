from __future__ import print_function
import os
import io
import json
import datetime
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Same scope as before
SCOPES = ['https://www.googleapis.com/auth/drive.file']

class DriveUploader:
    def __init__(self):
        # Use your existing main folder ID from original code
        self.main_folder_id = "1doyiFBYxHfdbLmqu2seRZJMbPH2940_z"

        # Build service using client credentials from env instead of credentials.json
        self.service = self._authenticate()

        print(f"✅ Connected to Shobha Sarees folder: {self.main_folder_id}")

    def _authenticate(self):
        """
        Authenticate using OAuth client creds from env var GOOGLE_APPLICATION_CREDENTIALS
        which contains the same JSON you previously had in credentials.json.
        No token.pickle is stored (serverless-safe).
        """
        creds_info_str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        if not creds_info_str:
            raise RuntimeError("Missing GOOGLE_APPLICATION_CREDENTIALS env var.")

        try:
            creds_info = json.loads(creds_info_str)
        except Exception as e:
            raise RuntimeError(f"GOOGLE_APPLICATION_CREDENTIALS is not valid JSON: {e}")

        # InstalledAppFlow expects a client_config dict in the same format as your credentials.json
        # Your provided JSON has the "installed" key already (fits flow.from_client_config).
        flow = InstalledAppFlow.from_client_config(creds_info, SCOPES)

        # In serverless, no local browser interaction.
        # Use console flow which prints a URL and expects a code.
        # For true hands-off, you should run once locally, save refresh token securely, and reuse.
        # Since you asked to keep it simple and similar, we’ll use run_console().
        # If you deploy this as-is, you’ll need to capture the code manually on first cold start.
        # To avoid that, replace this with pre-seeded refresh-token logic later.
        creds = flow.run_console()

        return build('drive', 'v3', credentials=creds, cache_discovery=False)

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
