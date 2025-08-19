from __future__ import print_function
import os
import io
import json
import datetime
import time
import logging
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
    from googleapiclient.errors import HttpError
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google.auth.exceptions import RefreshError
    GOOGLE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Google API libraries not available: {e}")
    GOOGLE_AVAILABLE = False

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Required scope for Google Drive operations
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Upload retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds
BACKOFF_MULTIPLIER = 2

class DriveUploader:
    """
    Enhanced Google Drive uploader with robust error handling,
    retry mechanisms, and comprehensive logging.
    """
    
    def __init__(self):
        """Initialize DriveUploader with enhanced error handling."""
        if not GOOGLE_AVAILABLE:
            raise RuntimeError("Google API libraries not available. Please install google-api-python-client and google-auth packages.")
        
        # Configuration
        self.main_folder_id = "1doyiFBYxHfdbLmqu2seRZJMbPH2940_z"
        self.service = None
        self.credentials = None
        
        # Performance tracking
        self.upload_stats = {
            'total_uploads': 0,
            'successful_uploads': 0,
            'failed_uploads': 0,
            'total_bytes_uploaded': 0,
            'average_upload_time': 0.0
        }
        
        # Initialize service
        try:
            self.service = self._authenticate()
            logger.info(f"✅ Google Drive connected successfully to folder: {self.main_folder_id}")
        except Exception as e:
            logger.error(f"❌ Google Drive authentication failed: {e}")
            raise RuntimeError(f"Drive authentication failed: {e}")

    def _authenticate(self) -> Any:
        """
        Enhanced authentication with comprehensive error handling.
        Supports both OAuth2 refresh token and service account methods.
        """
        # Method 1: Try OAuth2 refresh token (current method)
        try:
            return self._authenticate_oauth2()
        except Exception as oauth_error:
            logger.warning(f"OAuth2 authentication failed: {oauth_error}")
            
            # Method 2: Try service account (fallback)
            try:
                return self._authenticate_service_account()
            except Exception as sa_error:
                logger.error(f"Service account authentication also failed: {sa_error}")
                raise RuntimeError(f"All authentication methods failed. OAuth2: {oauth_error}, ServiceAccount: {sa_error}")

    def _authenticate_oauth2(self) -> Any:
        """OAuth2 authentication using refresh token."""
        # Get credentials from environment; accept JSON text or file path
        client_info_val = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        if not client_info_val:
            raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")

        refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN", "").strip()
        if not refresh_token:
            # Allow reading from file path for local development
            rt_path = os.getenv("GOOGLE_REFRESH_TOKEN_FILE", "").strip()
            if rt_path and os.path.exists(rt_path):
                refresh_token = Path(rt_path).read_text(encoding="utf-8").strip()
        if not refresh_token:
            raise RuntimeError("GOOGLE_REFRESH_TOKEN environment variable not set")

        # Parse client info; if a path, read file
        client_info_str: str
        if os.path.exists(client_info_val):
            client_info_str = Path(client_info_val).read_text(encoding="utf-8")
        else:
            client_info_str = client_info_val

        try:
            client_info = json.loads(client_info_str)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid GOOGLE_APPLICATION_CREDENTIALS (JSON or file) content: {e}")

        # Extract OAuth2 client details
        if "installed" not in client_info:
            raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS must contain 'installed' OAuth2 client configuration")

        installed = client_info["installed"]
        client_id = installed.get("client_id")
        client_secret = installed.get("client_secret")
        token_uri = installed.get("token_uri", "https://oauth2.googleapis.com/token")

        if not client_id or not client_secret:
            raise RuntimeError("Missing client_id or client_secret in OAuth2 configuration")

        # Create credentials
        self.credentials = Credentials(
            token=None,  # Will be fetched via refresh
            refresh_token=refresh_token,
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES,
        )

        # Refresh access token
        try:
            self.credentials.refresh(Request())
            logger.info("✅ OAuth2 credentials refreshed successfully")
        except RefreshError as e:
            raise RuntimeError(f"Token refresh failed: {e}. Check if GOOGLE_REFRESH_TOKEN is valid.")
        except Exception as e:
            raise RuntimeError(f"Unexpected error during token refresh: {e}")

        # Build and return service
        return build('drive', 'v3', credentials=self.credentials, cache_discovery=False)

    def _authenticate_service_account(self) -> Any:
        """Service account authentication (fallback method)."""
        try:
            from google.oauth2 import service_account
        except ImportError:
            raise RuntimeError("Service account authentication requires google-auth package")

        # Look for service account key in environment; accept JSON or file path
        service_account_info = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY", "").strip()
        if not service_account_info:
            sa_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY_FILE", "").strip()
            if sa_path and os.path.exists(sa_path):
                service_account_info = Path(sa_path).read_text(encoding="utf-8")
        if not service_account_info:
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_KEY not found for service account authentication")

        try:
            credentials_info = json.loads(service_account_info)
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info, 
                scopes=SCOPES
            )
            logger.info("✅ Service account authentication successful")
            return build('drive', 'v3', credentials=credentials, cache_discovery=False)
            
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid service account JSON: {e}")
        except Exception as e:
            raise RuntimeError(f"Service account authentication failed: {e}")

    def get_or_create_folder(self, folder_name: str, parent_id: str) -> str:
        """
        Get existing folder or create new one with enhanced error handling.
        
        Args:
            folder_name: Name of the folder
            parent_id: ID of the parent folder
            
        Returns:
            str: Folder ID
        """
        try:
            # Search for existing folder
            query = (
                f"name='{folder_name.replace('*', '_').replace('?', '_')}' and "
                f"mimeType='application/vnd.google-apps.folder' and "
                f"'{parent_id}' in parents and trashed = false"
            )
            
            results = self.service.files().list(
                q=query, 
                fields="files(id,name,createdTime)"
            ).execute()
            
            folders = results.get('files', [])
            
            if folders:
                folder = folders[0]  # Use the first matching folder
                logger.info(f"📁 Found existing folder: {folder_name} (ID: {folder['id']})")
                return folder['id']
            else:
                # Create new folder
                return self._create_folder(folder_name, parent_id)
                
        except HttpError as e:
            if e.resp.status == 403:
                raise RuntimeError(f"Permission denied: Cannot access parent folder {parent_id}")
            elif e.resp.status == 404:
                raise RuntimeError(f"Parent folder not found: {parent_id}")
            else:
                raise RuntimeError(f"Google Drive API error: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error in folder operations: {e}")

    def _create_folder(self, folder_name: str, parent_id: str) -> str:
        """Create a new folder with retry mechanism."""
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_id],
            'description': f'Auto-created folder for Shobha Sarees catalog: {folder_name}'
        }
        
        for attempt in range(MAX_RETRIES):
            try:
                folder = self.service.files().create(
                    body=folder_metadata, 
                    fields="id,name,createdTime"
                ).execute()
                
                logger.info(f"📁 Created new folder: {folder_name} (ID: {folder['id']})")
                return folder['id']
                
            except HttpError as e:
                if e.resp.status == 429:  # Rate limit
                    wait_time = RETRY_DELAY * (BACKOFF_MULTIPLIER ** attempt)
                    logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}/{MAX_RETRIES}")
                    time.sleep(wait_time)
                    continue
                else:
                    raise RuntimeError(f"Failed to create folder '{folder_name}': HTTP {e.resp.status}")
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    raise RuntimeError(f"Failed to create folder after {MAX_RETRIES} attempts: {e}")
                time.sleep(RETRY_DELAY * (BACKOFF_MULTIPLIER ** attempt))

    def upload_image(self, image_bytes: io.BytesIO, filename: str, catalog: Optional[str] = None) -> str:
        """
        Upload image with comprehensive error handling and retry mechanism.
        
        Args:
            image_bytes: Image data as BytesIO
            filename: Desired filename
            catalog: Optional catalog name for organization
            
        Returns:
            str: Google Drive file URL
        """
        upload_start_time = time.time()
        original_size = len(image_bytes.getvalue()) if hasattr(image_bytes, 'getvalue') else 0
        
        try:
            # Update stats
            self.upload_stats['total_uploads'] += 1
            
            # Determine parent folder
            parent_id = self.main_folder_id
            if catalog:
                parent_id = self.get_or_create_folder(catalog, self.main_folder_id)

            # Handle filename conflicts
            final_filename = self._resolve_filename_conflict(filename, parent_id)
            
            # Prepare file metadata
            file_metadata = {
                'name': final_filename,
                'parents': [parent_id],
                'description': f'Processed saree image - Catalog: {catalog or "General"}',
                'properties': {
                    'catalog': catalog or 'general',
                    'processed_by': 'shobha_sarees_photomaker',
                    'upload_timestamp': datetime.datetime.utcnow().isoformat(),
                    'original_size_bytes': str(original_size)
                }
            }
            
            # Upload with retry mechanism
            file_url = self._upload_with_retries(image_bytes, file_metadata, final_filename)
            
            # Update success stats
            upload_time = time.time() - upload_start_time
            self.upload_stats['successful_uploads'] += 1
            self.upload_stats['total_bytes_uploaded'] += original_size
            self._update_average_upload_time(upload_time)
            
            logger.info(f"✅ Successfully uploaded: {final_filename} ({original_size} bytes in {upload_time:.2f}s)")
            return file_url
            
        except Exception as e:
            # Update failure stats
            self.upload_stats['failed_uploads'] += 1
            upload_time = time.time() - upload_start_time
            
            logger.error(f"❌ Upload failed for {filename}: {e} (after {upload_time:.2f}s)")
            raise e

    def _resolve_filename_conflict(self, filename: str, parent_id: str) -> str:
        """Resolve filename conflicts by appending timestamp if needed."""
        try:
            # Check if file already exists
            query = f"name='{filename}' and '{parent_id}' in parents and trashed = false"
            existing_files = self.service.files().list(
                q=query, 
                fields="files(id,name)"
            ).execute().get('files', [])
            
            if existing_files:
                # Append timestamp to avoid conflict
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                name_parts = filename.rsplit('.', 1)
                
                if len(name_parts) == 2:
                    final_filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
                else:
                    final_filename = f"{filename}_{timestamp}"
                    
                logger.info(f"⚠️ Filename conflict resolved: {filename} → {final_filename}")
                return final_filename
            else:
                return filename
                
        except Exception as e:
            # If conflict check fails, use timestamp anyway to be safe
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            name_parts = filename.rsplit('.', 1)
            if len(name_parts) == 2:
                return f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
            else:
                return f"{filename}_{timestamp}"

    def _upload_with_retries(self, image_bytes: io.BytesIO, file_metadata: Dict[str, Any], filename: str) -> str:
        """Upload file with exponential backoff retry mechanism."""
        for attempt in range(MAX_RETRIES):
            try:
                # Reset BytesIO position for retry
                image_bytes.seek(0)
                
                # Create media upload object
                media = MediaIoBaseUpload(
                    image_bytes, 
                    mimetype='image/jpeg',
                    resumable=True,
                    chunksize=1024*1024  # 1MB chunks for better reliability
                )
                
                # Upload file
                request = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id,name,webViewLink,size,createdTime'
                )
                
                # Execute upload with progress tracking
                file_result = None
                while file_result is None:
                    status, file_result = request.next_chunk()
                    if status:
                        logger.debug(f"Upload progress: {int(status.progress() * 100)}% for {filename}")
                
                # Verify upload success
                if not file_result or 'id' not in file_result:
                    raise RuntimeError("Upload completed but no file ID returned")
                
                logger.info(f"📤 Upload completed: {filename} (ID: {file_result['id']})")
                return file_result.get('webViewLink', f"https://drive.google.com/file/d/{file_result['id']}/view")
                
            except HttpError as e:
                error_code = e.resp.status
                
                if error_code == 403:
                    if 'dailyLimitExceeded' in str(e) or 'quotaExceeded' in str(e):
                        raise RuntimeError("Google Drive quota exceeded. Please try again later.")
                    else:
                        raise RuntimeError(f"Permission denied: {e}")
                        
                elif error_code == 404:
                    raise RuntimeError(f"Parent folder not found: {e}")
                    
                elif error_code == 429:  # Rate limit
                    if attempt < MAX_RETRIES - 1:
                        wait_time = RETRY_DELAY * (BACKOFF_MULTIPLIER ** attempt) + (attempt * 2)
                        logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}/{MAX_RETRIES}")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise RuntimeError("Upload failed due to rate limiting after maximum retries")
                        
                elif 500 <= error_code < 600:  # Server errors
                    if attempt < MAX_RETRIES - 1:
                        wait_time = RETRY_DELAY * (BACKOFF_MULTIPLIER ** attempt)
                        logger.warning(f"Server error {error_code}, retrying in {wait_time}s (attempt {attempt + 1}/{MAX_RETRIES})")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise RuntimeError(f"Upload failed due to server errors after {MAX_RETRIES} attempts: {e}")
                        
                else:
                    raise RuntimeError(f"Upload failed with HTTP {error_code}: {e}")
                    
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (BACKOFF_MULTIPLIER ** attempt)
                    logger.warning(f"Upload attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    raise RuntimeError(f"Upload failed after {MAX_RETRIES} attempts: {e}")

    def _update_average_upload_time(self, new_time: float) -> None:
        """Update running average of upload times."""
        if self.upload_stats['successful_uploads'] == 1:
            self.upload_stats['average_upload_time'] = new_time
        else:
            # Running average calculation
            prev_avg = self.upload_stats['average_upload_time']
            count = self.upload_stats['successful_uploads']
            self.upload_stats['average_upload_time'] = prev_avg + (new_time - prev_avg) / count

    def get_upload_stats(self) -> Dict[str, Any]:
        """Get comprehensive upload statistics."""
        success_rate = 0.0
        if self.upload_stats['total_uploads'] > 0:
            success_rate = (self.upload_stats['successful_uploads'] / self.upload_stats['total_uploads']) * 100
            
        total_mb = self.upload_stats['total_bytes_uploaded'] / (1024 * 1024)
        
        return {
            **self.upload_stats,
            'success_rate_percent': round(success_rate, 2),
            'total_mb_uploaded': round(total_mb, 2),
            'average_upload_time_seconds': round(self.upload_stats['average_upload_time'], 2)
        }

    def test_connection(self) -> Tuple[bool, str]:
        """
        Test Google Drive connection and permissions.
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Test basic API access
            about = self.service.about().get(fields='user,storageQuota').execute()
            user_email = about.get('user', {}).get('emailAddress', 'Unknown')
            
            # Test folder access
            folder = self.service.files().get(
                fileId=self.main_folder_id,
                fields='id,name,permissions'
            ).execute()
            
            folder_name = folder.get('name', 'Unknown')
            
            # Test write permissions by checking if we can list files
            self.service.files().list(
                q=f"'{self.main_folder_id}' in parents",
                pageSize=1,
                fields='files(id)'
            ).execute()
            
            return True, f"✅ Connected as {user_email}, folder: {folder_name}"
            
        except HttpError as e:
            if e.resp.status == 403:
                return False, f"❌ Permission denied: Check folder sharing settings"
            elif e.resp.status == 404:
                return False, f"❌ Main folder not found: {self.main_folder_id}"
            else:
                return False, f"❌ API Error: HTTP {e.resp.status}"
        except Exception as e:
            return False, f"❌ Connection test failed: {str(e)}"

    def cleanup_temp_files(self, older_than_hours: int = 24) -> int:
        """
        Clean up temporary/test files older than specified hours.
        
        Args:
            older_than_hours: Files older than this will be deleted
            
        Returns:
            int: Number of files deleted
        """
        try:
            cutoff_time = datetime.datetime.utcnow() - datetime.timedelta(hours=older_than_hours)
            cutoff_iso = cutoff_time.isoformat() + 'Z'
            
            # Search for files with temp indicators in name
            query = (
                f"'{self.main_folder_id}' in parents and "
                f"(name contains '_temp_' or name contains '_test_') and "
                f"createdTime < '{cutoff_iso}' and "
                f"trashed = false"
            )
            
            results = self.service.files().list(
                q=query,
                fields='files(id,name,createdTime)'
            ).execute()
            
            files_to_delete = results.get('files', [])
            deleted_count = 0
            
            for file in files_to_delete:
                try:
                    self.service.files().delete(fileId=file['id']).execute()
                    logger.info(f"🗑️ Deleted temp file: {file['name']}")
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete {file['name']}: {e}")
            
            if deleted_count > 0:
                logger.info(f"✅ Cleanup completed: {deleted_count} temp files deleted")
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return 0

    def __del__(self):
        """Cleanup on destruction."""
        if hasattr(self, 'upload_stats') and self.upload_stats['total_uploads'] > 0:
            stats = self.get_upload_stats()
            logger.info(f"📊 DriveUploader session stats: {stats}")
