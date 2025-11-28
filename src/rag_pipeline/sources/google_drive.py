import io
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from src.rag_pipeline.adapters.agentic_rag_adapter import process_file_with_agentic_rag_sync
from src.rag_pipeline.common.db_handler import delete_document_by_file_id
from src.rag_pipeline.common.text_processor import extract_text_from_file

structlog_logger = structlog.get_logger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


class GoogleDriveWatcher:
    def __init__(
        self,
        credentials_path: str = "credentials.json",
        token_path: str = "token.json",  # nosec B107 - this is a filename, not a password
        folder_id: str | None = None,
        config_path: str | None = None,
    ):
        """
        Initialize the Google Drive watcher.

        Args:
            credentials_path: Path to the credentials.json file
            token_path: Path to the token.json file
            folder_id: ID of the specific Google Drive folder to watch (None to watch all files)
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.folder_id = folder_id
        self.service = None
        self.known_files: dict[str, str] = {}  # Store file IDs and their last modified time
        self.initialized = False  # Flag to track if we've done the initial scan

        # Load configuration
        self.config: dict[str, Any] = {}
        if config_path:
            self.config_path = config_path
        else:
            # Default to config.json in the same directory as this script
            self.config_path = str(Path(__file__).parent.resolve() / "config.json")
        self.load_config()

    def load_config(self) -> None:
        """
        Load configuration from JSON file.
        """
        structlog_logger.info("load_config called", config_path=self.config_path)
        try:
            with Path(self.config_path).open() as f:
                self.config = json.load(f)
            structlog_logger.info(
                "Configuration loaded successfully",
                config_path=self.config_path,
                num_supported_types=len(self.config.get("supported_mime_types", [])),
            )

            # Load the last check time from config
            last_check_time_str = self.config.get("last_check_time", "1970-01-01T00:00:00.000Z")
            try:
                self.last_check_time = datetime.strptime(
                    last_check_time_str, "%Y-%m-%dT%H:%M:%S.%fZ"
                )
                structlog_logger.info(
                    "Resuming from last check time", last_check_time=str(self.last_check_time)
                )
            except ValueError:
                # If the date format is invalid, use the default
                self.last_check_time = datetime.strptime(
                    "1970-01-01T00:00:00.000Z", "%Y-%m-%dT%H:%M:%S.%fZ"
                )
                structlog_logger.warning(
                    "Invalid last check time format in config, using default",
                    invalid_format=last_check_time_str,
                )

            if not self.folder_id:
                self.folder_id = self.config.get("watch_folder_id", None)
                structlog_logger.info("Loaded folder ID from config", folder_id=self.folder_id)

        except Exception as e:
            structlog_logger.error(
                "Error loading configuration, using defaults",
                error=str(e),
                config_path=self.config_path,
            )
            self.config = {
                "supported_mime_types": [
                    "application/pdf",
                    "text/plain",
                    "text/html",
                    "text/csv",
                    "application/vnd.google-apps.document",
                    "application/vnd.google-apps.spreadsheet",
                    "application/vnd.google-apps.presentation",
                ],
                "export_mime_types": {
                    "application/vnd.google-apps.document": "text/plain",
                    "application/vnd.google-apps.spreadsheet": "text/csv",
                    "application/vnd.google-apps.presentation": "text/plain",
                },
                "text_processing": {"default_chunk_size": 400, "default_chunk_overlap": 0},
                "last_check_time": "1970-01-01T00:00:00.000Z",
            }
            self.last_check_time = datetime.strptime(
                "1970-01-01T00:00:00.000Z", "%Y-%m-%dT%H:%M:%S.%fZ"
            )
            structlog_logger.info("Using default configuration")

        structlog_logger.info(
            "load_config completed",
            has_folder_id=self.folder_id is not None,
            last_check_time=str(self.last_check_time),
        )

    def save_last_check_time(self) -> None:
        """
        Save the last check time to the config file.
        """
        structlog_logger.info(
            "save_last_check_time called",
            last_check_time=str(self.last_check_time),
            config_path=self.config_path,
        )
        try:
            # Update the last_check_time in the config
            self.config["last_check_time"] = self.last_check_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

            # Write the updated config back to the file
            with Path(self.config_path).open("w") as f:
                json.dump(self.config, f, indent=2)

            structlog_logger.info(
                "Last check time saved successfully",
                last_check_time=str(self.last_check_time),
                config_path=self.config_path,
            )
        except Exception as e:
            structlog_logger.error(
                "Error saving last check time",
                error=str(e),
                last_check_time=str(self.last_check_time),
                config_path=self.config_path,
            )

    def authenticate(self) -> None:
        """
        Authenticate with Google Drive API.
        """
        structlog_logger.info(
            "authenticate called",
            token_path=self.token_path,
            credentials_path=self.credentials_path,
        )
        creds = None

        # Check if token.json exists
        if Path(self.token_path).exists():
            structlog_logger.info("Loading existing token", token_path=self.token_path)
            with Path(self.token_path).open() as token_file:
                creds = Credentials.from_authorized_user_info(json.loads(token_file.read()), SCOPES)  # type: ignore[no-untyped-call]
            structlog_logger.info("Token loaded successfully")

        # If there are no valid credentials, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                structlog_logger.info("Token expired, attempting refresh")
                try:
                    creds.refresh(Request())  # type: ignore[no-untyped-call]
                    structlog_logger.info("Token refreshed successfully")
                except RefreshError:
                    # If refresh fails, re-authenticate
                    structlog_logger.warning("Token refresh failed, re-authenticating")
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                    structlog_logger.info("Re-authentication completed")
            else:
                structlog_logger.info("No valid credentials, starting authentication flow")
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_path, SCOPES)
                try:
                    creds = flow.run_local_server(port=0)
                    structlog_logger.info("Authentication completed")
                except Exception as e:
                    structlog_logger.warning(
                        "Local server OAuth failed, falling back to manual flow", error=str(e)
                    )
                    print("\n" + "=" * 80)
                    print("WSL/headless environment detected. Using manual authorization flow.")
                    print("=" * 80)
                    auth_url, _ = flow.authorization_url(prompt="consent")
                    print(f"\nPlease visit this URL in your browser:\n{auth_url}\n")
                    print("After authorizing, you'll be redirected to a URL starting with:")
                    print("http://localhost/?state=...&code=...\n")
                    code = input("Paste the FULL URL here: ").strip()
                    # Extract code from URL if full URL was pasted
                    if "code=" in code:
                        code = code.split("code=")[1].split("&")[0]
                    flow.fetch_token(code=code)
                    creds = flow.credentials
                    structlog_logger.info("Manual authentication completed")

            # Save the credentials for the next run
            with Path(self.token_path).open("w") as token:
                token.write(creds.to_json())
            structlog_logger.info("Credentials saved", token_path=self.token_path)

        # Build the Drive API service
        self.service = build("drive", "v3", credentials=creds)
        structlog_logger.info("Google Drive API service built successfully")

    def get_folder_contents(self, folder_id: str, time_str: str) -> list[dict[str, Any]]:
        """
        Get all files and subfolders in a folder that have been modified or created after the specified time.

        Args:
            folder_id: The ID of the folder to check
            time_str: The time string in RFC 3339 format

        Returns:
            List of files and folders with their metadata
        """
        structlog_logger.info("get_folder_contents called", folder_id=folder_id, time_str=time_str)

        if not self.service:
            structlog_logger.info("Service not initialized, authenticating")
            self.authenticate()

        if not self.service:
            structlog_logger.error("Failed to authenticate, returning empty list")
            return []

        # Query for files in this folder that were modified OR created after the specified time
        query = f"(modifiedTime > '{time_str}' or createdTime > '{time_str}') and '{folder_id}' in parents"
        structlog_logger.info("Querying folder contents", query=query)

        results = (
            self.service.files()
            .list(
                q=query,
                pageSize=100,
                fields="nextPageToken, files(id, name, mimeType, webViewLink, modifiedTime, createdTime, trashed)",
            )
            .execute()
        )

        items = results.get("files", [])
        structlog_logger.info(
            "Files retrieved from folder", folder_id=folder_id, num_files=len(items)
        )

        # Find all subfolders in this folder (regardless of modification time)
        folder_query = (
            f"'{folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder'"
        )
        if not self.service:
            structlog_logger.error("Service became unavailable during subfolder query")
            return items

        folder_results = (
            self.service.files().list(q=folder_query, pageSize=100, fields="files(id)").execute()
        )

        subfolders = folder_results.get("files", [])
        structlog_logger.info(
            "Subfolders found", folder_id=folder_id, num_subfolders=len(subfolders)
        )

        # Recursively get contents of each subfolder
        for subfolder in subfolders:
            structlog_logger.info(
                "Processing subfolder", subfolder_id=subfolder["id"], parent_folder_id=folder_id
            )
            subfolder_items = self.get_folder_contents(subfolder["id"], time_str)
            items.extend(subfolder_items)
            structlog_logger.info(
                "Subfolder processed",
                subfolder_id=subfolder["id"],
                items_added=len(subfolder_items),
            )

        structlog_logger.info(
            "get_folder_contents completed", folder_id=folder_id, total_items=len(items)
        )
        return items

    def get_changes(self) -> list[dict[str, Any]]:
        """
        Get changes in Google Drive since the last check.

        Returns:
            List of changed files with their metadata
        """
        structlog_logger.info(
            "get_changes called",
            last_check_time=str(self.last_check_time),
            folder_id=self.folder_id,
        )

        if not self.service:
            structlog_logger.info("Service not initialized, authenticating")
            self.authenticate()

        if not self.service:
            structlog_logger.error("Failed to authenticate, returning empty list")
            return []

        # Convert last_check_time to RFC 3339 format
        time_str = self.last_check_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        structlog_logger.info("Checking for changes since", time_str=time_str)

        files = []

        # If a specific folder is specified, recursively get all files in that folder and its subfolders
        if self.folder_id:
            structlog_logger.info("Querying specific folder", folder_id=self.folder_id)
            files = self.get_folder_contents(self.folder_id, time_str)
        else:
            # If no folder is specified, get all files in the drive that were modified OR created after the specified time
            structlog_logger.info("Querying entire drive for changes")
            query = f"modifiedTime > '{time_str}' or createdTime > '{time_str}'"
            results = (
                self.service.files()
                .list(
                    q=query,
                    pageSize=100,
                    fields="nextPageToken, files(id, name, mimeType, webViewLink, modifiedTime, createdTime, trashed)",
                )
                .execute()
            )

            files = results.get("files", [])
            structlog_logger.info("Drive-wide query completed", num_files=len(files))

        # Update the last check time
        old_check_time = self.last_check_time
        self.last_check_time = datetime.now(UTC)
        structlog_logger.info(
            "Updated last check time",
            old_time=str(old_check_time),
            new_time=str(self.last_check_time),
        )

        # Save the updated last check time to config
        self.save_last_check_time()

        structlog_logger.info("get_changes completed", total_changes=len(files))
        return files

    def download_file(self, file_id: str, mime_type: str) -> bytes | None:
        """
        Download a file from Google Drive.

        Args:
            file_id: The ID of the file to download
            mime_type: The MIME type of the file

        Returns:
            The file content as bytes, or None if download failed
        """
        structlog_logger.info("download_file called", file_id=file_id, mime_type=mime_type)

        if not self.service:
            structlog_logger.info("Service not initialized, authenticating")
            self.authenticate()

        if not self.service:
            structlog_logger.error("Failed to authenticate, cannot download file", file_id=file_id)
            return None

        try:
            file_content = io.BytesIO()

            # Check if this is a Google Workspace file that needs to be exported
            export_mime_types = self.config.get("export_mime_types", {})
            if mime_type in export_mime_types:
                # Export the file in the appropriate format
                export_mime_type = export_mime_types[mime_type]
                structlog_logger.info(
                    "Exporting Google Workspace file",
                    file_id=file_id,
                    from_mime=mime_type,
                    to_mime=export_mime_type,
                )
                request = self.service.files().export_media(
                    fileId=file_id, mimeType=export_mime_type
                )
            else:
                # For regular files, download directly
                structlog_logger.info(
                    "Downloading regular file", file_id=file_id, mime_type=mime_type
                )
                request = self.service.files().get_media(fileId=file_id)

            # Download the file
            downloader = MediaIoBaseDownload(file_content, request)
            done = False
            chunks_downloaded = 0
            while not done:
                _status, done = downloader.next_chunk()
                chunks_downloaded += 1

            structlog_logger.info(
                "File download completed", file_id=file_id, chunks_downloaded=chunks_downloaded
            )

            # Reset the pointer to the beginning of the file
            file_content.seek(0)
            content_bytes = file_content.read()
            content_size = len(content_bytes)
            structlog_logger.info("File content ready", file_id=file_id, size_bytes=content_size)
            return content_bytes

        except Exception as e:
            structlog_logger.error(
                "Error downloading file", error=str(e), file_id=file_id, mime_type=mime_type
            )
            return None

    def process_file(self, file: dict[str, Any]) -> None:
        """
        Process a file for the RAG pipeline.

        Args:
            file: The file metadata from Google Drive
        """
        file_id = file["id"]
        file_name = file["name"]
        mime_type = file["mimeType"]
        web_view_link = file.get("webViewLink", "")
        is_trashed = file.get("trashed", False)

        structlog_logger.info(
            "process_file called",
            file_id=file_id,
            file_name=file_name,
            mime_type=mime_type,
            is_trashed=is_trashed,
        )

        # Check if the file is in the trash
        if is_trashed:
            structlog_logger.info(
                "File trashed, removing from database", file_id=file_id, file_name=file_name
            )
            delete_document_by_file_id(file_id)
            if file_id in self.known_files:
                del self.known_files[file_id]
            structlog_logger.info("Trashed file removed from database", file_id=file_id)
            return

        # Skip unsupported file types
        supported_mime_types = self.config.get("supported_mime_types", [])
        if not any(mime_type.startswith(t) for t in supported_mime_types):
            structlog_logger.info(
                "Skipping unsupported file type",
                file_id=file_id,
                file_name=file_name,
                mime_type=mime_type,
            )
            return

        # Download the file
        structlog_logger.info("Starting file download", file_id=file_id, file_name=file_name)
        file_content = self.download_file(file_id, mime_type)
        if not file_content:
            structlog_logger.error("Failed to download file", file_id=file_id, file_name=file_name)
            return

        # Extract text from the file
        structlog_logger.info(
            "Extracting text from file",
            file_id=file_id,
            file_name=file_name,
            content_size=len(file_content),
        )
        text = extract_text_from_file(file_content, mime_type, file_name, self.config)
        if not text:
            structlog_logger.warning(
                "No text extracted from file", file_id=file_id, file_name=file_name
            )
            return

        text_length = len(text)
        structlog_logger.info(
            "Text extraction completed",
            file_id=file_id,
            file_name=file_name,
            text_length=text_length,
        )

        # Delete existing records (Agentic RAG doesn't handle updates yet)
        structlog_logger.info("Deleting existing records for file", file_id=file_id)
        delete_document_by_file_id(file_id)

        # Process the file with Agentic RAG pipeline
        structlog_logger.info(
            "Processing file with Agentic RAG pipeline",
            file_id=file_id,
            file_name=file_name,
        )
        success = process_file_with_agentic_rag_sync(
            text=text,
            file_id=file_id,
            file_title=file_name,
            file_url=web_view_link,
            mime_type=mime_type,
            use_rest_api=False,  # Try PostgreSQL first, fallback to REST
        )

        # Update the known files dictionary
        modified_time = file.get("modifiedTime")
        self.known_files[file_id] = modified_time if modified_time is not None else ""

        if success:
            structlog_logger.info(
                "File processed successfully", file_id=file_id, file_name=file_name
            )
        else:
            structlog_logger.error(
                "Failed to process file for RAG", file_id=file_id, file_name=file_name
            )

    def check_for_deleted_files(self) -> list[str]:
        """
        Check for files that have been deleted from Google Drive.

        Returns:
            List of IDs of deleted files
        """
        structlog_logger.info(
            "check_for_deleted_files called", num_known_files=len(self.known_files)
        )

        if not self.service:
            structlog_logger.info("Service not initialized, authenticating")
            self.authenticate()

        if not self.service:
            structlog_logger.error("Failed to authenticate, returning empty list")
            return []

        # We'll only check files we know about
        deleted_files: list[str] = []

        # Only check if we have known files
        if not self.known_files:
            structlog_logger.info("No known files to check for deletion")
            return deleted_files

        # Check each known file to see if it still exists or has been trashed
        structlog_logger.info(
            "Checking known files for deletion", num_files_to_check=len(self.known_files)
        )
        files_checked = 0
        for file_id in list(self.known_files.keys()):
            files_checked += 1
            try:
                # Get the file metadata
                file = self.service.files().get(fileId=file_id, fields="trashed,name").execute()

                # If the file is in the trash, consider it deleted
                if file.get("trashed", False):
                    file_name = file.get("name", "Unknown")
                    structlog_logger.info(
                        "File found in trash", file_id=file_id, file_name=file_name
                    )
                    deleted_files.append(file_id)
            except Exception as e:
                error_str = str(e)
                # If we get an error (like file not found), the file is deleted
                if "File not found" in error_str or "404" in error_str:
                    structlog_logger.info("File not found (deleted)", file_id=file_id)
                    deleted_files.append(file_id)
                else:
                    structlog_logger.error(
                        "Error checking file status", error=error_str, file_id=file_id
                    )

        structlog_logger.info(
            "check_for_deleted_files completed",
            files_checked=files_checked,
            deleted_files_found=len(deleted_files),
        )
        return deleted_files

    def watch_for_changes(self, interval_seconds: int = 60) -> None:
        """
        Watch for changes in Google Drive at regular intervals.

        Args:
            interval_seconds: The interval in seconds between checks
        """
        folder_msg = f" in folder ID: {self.folder_id}" if self.folder_id else ""
        structlog_logger.info(
            "watch_for_changes called",
            interval_seconds=interval_seconds,
            folder_id=self.folder_id,
            has_folder_filter=bool(self.folder_id),
        )
        structlog_logger.info(
            f"Starting Google Drive watcher{folder_msg}. Checking for changes every {interval_seconds} seconds..."
        )

        try:
            # Authenticate if needed
            if not self.service:
                structlog_logger.info("Service not initialized, authenticating")
                self.authenticate()

            if not self.service:
                structlog_logger.error(
                    "Failed to authenticate with Google Drive, cannot start watcher"
                )
                return

            # Initial scan to build the known_files dictionary
            if not self.initialized:
                structlog_logger.info("Performing initial scan of files...")
                # Get all files in the watched folder
                # Use the last check time from config or default to 1970-01-01
                time_str = self.last_check_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                if self.folder_id:
                    structlog_logger.info(
                        "Scanning specific folder", folder_id=self.folder_id, time_str=time_str
                    )
                    files = self.get_folder_contents(self.folder_id, time_str)  # Get all files
                else:
                    # If watching all of Drive, get all files
                    structlog_logger.info("Scanning entire drive", time_str=time_str)
                    results = (
                        self.service.files()
                        .list(
                            pageSize=1000,
                            fields="nextPageToken, files(id, name, mimeType, webViewLink, modifiedTime, trashed)",
                        )
                        .execute()
                    )
                    files = results.get("files", [])

                # Build the known_files dictionary - only store the modifiedTime
                for file in files:
                    if not file.get("trashed", False):  # Skip files in trash
                        # Only store the modifiedTime to avoid processing all files
                        modified_time = file.get("modifiedTime")
                        self.known_files[file["id"]] = (
                            modified_time if modified_time is not None else ""
                        )

                structlog_logger.info(
                    "Initial scan completed", num_files_found=len(self.known_files)
                )
                self.initialized = True

            cycle_count = 0
            while True:
                cycle_count += 1
                structlog_logger.info("=" * 80)
                structlog_logger.info(
                    "Starting watch cycle", cycle=cycle_count, interval_seconds=interval_seconds
                )

                # Get changes since the last check
                changed_files = self.get_changes()

                # Check for deleted files (every 5 cycles to reduce API calls)
                deleted_file_ids = []

                deleted_file_ids = self.check_for_deleted_files()

                # Process changed files
                if changed_files:
                    structlog_logger.info(
                        "Processing changed files", num_changed_files=len(changed_files)
                    )
                    for idx, file in enumerate(changed_files, 1):
                        structlog_logger.info(
                            "Processing changed file",
                            file_num=idx,
                            total=len(changed_files),
                            file_id=file.get("id"),
                            file_name=file.get("name"),
                        )
                        self.process_file(file)
                        # Update known_files with just the modifiedTime
                        modified_time = file.get("modifiedTime")
                        self.known_files[file["id"]] = (
                            modified_time if modified_time is not None else ""
                        )
                    structlog_logger.info(
                        "Changed files processed", num_processed=len(changed_files)
                    )
                else:
                    structlog_logger.info("No changed files found in this cycle")

                # Process deleted files
                if deleted_file_ids:
                    structlog_logger.info(
                        "Processing deleted files", num_deleted_files=len(deleted_file_ids)
                    )
                    for idx, file_id in enumerate(deleted_file_ids, 1):
                        structlog_logger.info(
                            "Processing deleted file",
                            file_num=idx,
                            total=len(deleted_file_ids),
                            file_id=file_id,
                        )
                        delete_document_by_file_id(file_id)
                        # Remove from known_files
                        del self.known_files[file_id]
                    structlog_logger.info(
                        "Deleted files processed", num_processed=len(deleted_file_ids)
                    )
                else:
                    structlog_logger.info("No deleted files found in this cycle")

                # Wait for the next check
                structlog_logger.info(
                    "Watch cycle completed", cycle=cycle_count, waiting_seconds=interval_seconds
                )
                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            structlog_logger.info("Watcher stopped by user (KeyboardInterrupt)")
        except Exception as e:
            structlog_logger.error("Error in watcher", error=str(e))
            raise
