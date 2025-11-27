import json
import mimetypes
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from src.rag_pipeline.adapters.agentic_rag_adapter import process_file_with_agentic_rag_sync
from src.rag_pipeline.common.db_handler import delete_document_by_file_id
from src.rag_pipeline.common.text_processor import extract_text_from_file

structlog_logger = structlog.get_logger(__name__)


class LocalFileWatcher:
    def __init__(self, watch_directory: str | None = None, config_path: str | None = None):
        """
        Initialize the Local File watcher.

        Args:
            watch_directory: Directory to watch for files (relative to this script)
            config_path: Path to the configuration file
        """
        structlog_logger.info(
            "LocalFileWatcher.__init__ called",
            watch_directory=watch_directory,
            config_path=config_path,
        )

        # Load configuration
        self.config: dict[str, Any] = {}
        if config_path:
            self.config_path = config_path
        else:
            # Default to config.json in the same directory as this script
            self.config_path = str(Path(__file__).parent.resolve() / "config.json")

        structlog_logger.info("Loading configuration", config_path=self.config_path)
        self.load_config()

        # Set up the watch directory
        if watch_directory:
            self.watch_directory = watch_directory
        else:
            self.watch_directory = self.config.get("watch_directory", "data")

        # Make the watch directory absolute
        self.watch_directory = str(Path(__file__).parent.resolve() / self.watch_directory)

        structlog_logger.info(
            "Creating watch directory if needed", watch_directory=self.watch_directory
        )
        # Create the watch directory if it doesn't exist
        Path(self.watch_directory).mkdir(parents=True, exist_ok=True)

        self.known_files: dict[str, str] = {}  # Store file paths and their last modified time
        self.initialized = False  # Flag to track if we've done the initial scan

        # Initialize mimetypes
        mimetypes.init()

        structlog_logger.info(
            "LocalFileWatcher initialized",
            watch_directory=self.watch_directory,
            config_path=self.config_path,
            initialized=self.initialized,
        )

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
                num_keys=len(self.config),
            )

            # Load the last check time from config
            last_check_time_str = self.config.get("last_check_time", "1970-01-01T00:00:00.000Z")
            try:
                self.last_check_time = datetime.strptime(
                    last_check_time_str, "%Y-%m-%dT%H:%M:%S.%fZ"
                )
                structlog_logger.info(
                    "Last check time loaded", last_check_time=str(self.last_check_time)
                )
            except ValueError as ve:
                # If the date format is invalid, use the default
                self.last_check_time = datetime.strptime(
                    "1970-01-01T00:00:00.000Z", "%Y-%m-%dT%H:%M:%S.%fZ"
                )
                structlog_logger.warning(
                    "Invalid last check time format, using default",
                    error=str(ve),
                    last_check_time_str=last_check_time_str,
                )

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
                    "text/csv",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ],
                "tabular_mime_types": [
                    "text/csv",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ],
                "text_processing": {"default_chunk_size": 400, "default_chunk_overlap": 0},
                "last_check_time": "1970-01-01T00:00:00.000Z",
            }
            self.last_check_time = datetime.strptime(
                "1970-01-01T00:00:00.000Z", "%Y-%m-%dT%H:%M:%S.%fZ"
            )
            structlog_logger.info(
                "Using default configuration",
                num_mime_types=len(self.config["supported_mime_types"]),
            )

    def save_last_check_time(self) -> None:
        """
        Save the last check time to the config file.
        """
        structlog_logger.info(
            "save_last_check_time called", last_check_time=str(self.last_check_time)
        )
        try:
            # Update the last_check_time in the config
            self.config["last_check_time"] = self.last_check_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

            structlog_logger.info("Writing config to file", config_path=self.config_path)
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

    def get_mime_type(self, file_path: str) -> str:
        """
        Get the MIME type of a file.

        Args:
            file_path: Path to the file

        Returns:
            str: MIME type of the file
        """
        structlog_logger.info("get_mime_type called", file_path=file_path)

        # Custom mappings for common file extensions
        extension_mappings = {
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xls": "application/vnd.ms-excel",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".doc": "application/msword",
            ".csv": "text/csv",
            ".pdf": "application/pdf",
            ".txt": "text/plain",
        }

        # Get file extension
        ext = Path(file_path.lower()).suffix
        structlog_logger.info("File extension extracted", file_path=file_path, extension=ext)

        # Check if extension is in our custom mappings
        mime_type: str | None
        if ext in extension_mappings:
            mime_type = extension_mappings[ext]
            structlog_logger.info(
                "MIME type determined from custom mapping", file_path=file_path, mime_type=mime_type
            )
            return mime_type

        # Fall back to mimetypes module
        mime_type_guess, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type_guess
        if mime_type is None:
            # Default to plain text if can't determine
            mime_type = "text/plain"
            structlog_logger.warning(
                "Could not determine MIME type, using default",
                file_path=file_path,
                mime_type=mime_type,
            )
        else:
            structlog_logger.info(
                "MIME type determined from mimetypes module",
                file_path=file_path,
                mime_type=mime_type,
            )

        return mime_type

    def get_file_content(self, file_path: str) -> bytes | None:
        """
        Read the content of a file.

        Args:
            file_path: Path to the file

        Returns:
            bytes: Content of the file, or None if reading fails
        """
        structlog_logger.info("get_file_content called", file_path=file_path)
        try:
            with Path(file_path).open("rb") as f:
                content = f.read()
            content_size = len(content)
            structlog_logger.info(
                "File content read successfully",
                file_path=file_path,
                content_size_bytes=content_size,
            )
            return content
        except Exception as e:
            structlog_logger.error("Error reading file content", error=str(e), file_path=file_path)
            return None

    def get_changes(self) -> list[dict[str, Any]]:
        """
        Get files that have been created or modified since the last check.

        Returns:
            List[Dict[str, Any]]: List of file information dictionaries
        """
        structlog_logger.info(
            "get_changes called",
            watch_directory=self.watch_directory,
            last_check_time=str(self.last_check_time),
        )
        changed_files = []

        # Walk through the watch directory
        structlog_logger.info(
            "Walking through watch directory", watch_directory=self.watch_directory
        )
        for root, _, files in os.walk(self.watch_directory):
            for file_name in files:
                file_path = str(Path(root) / file_name)
                file_stat = Path(file_path).stat()

                # Convert to datetime for comparison
                mod_time = datetime.fromtimestamp(file_stat.st_mtime)
                create_time = datetime.fromtimestamp(file_stat.st_ctime)

                # Check if the file is new or modified
                if (
                    file_path not in self.known_files
                    or mod_time > self.last_check_time
                    or create_time > self.last_check_time
                ):
                    structlog_logger.info(
                        "File changed detected",
                        file_path=file_path,
                        file_name=file_name,
                        is_new=file_path not in self.known_files,
                        mod_time=str(mod_time),
                        create_time=str(create_time),
                    )

                    # Get MIME type
                    mime_type = self.get_mime_type(file_path)

                    # Create a file info dictionary similar to Google Drive
                    file_info = {
                        "id": file_path,  # Use file path as ID
                        "name": file_name,
                        "mimeType": mime_type,
                        "webViewLink": f"file://{file_path}",  # Local file URL
                        "modifiedTime": mod_time.isoformat(),
                        "createdTime": create_time.isoformat(),
                        "trashed": False,
                    }

                    changed_files.append(file_info)

        # Update the last check time
        old_check_time = self.last_check_time
        self.last_check_time = datetime.now()
        structlog_logger.info(
            "Updating last check time",
            old_check_time=str(old_check_time),
            new_check_time=str(self.last_check_time),
        )

        # Save the updated last check time to config
        self.save_last_check_time()

        structlog_logger.info("get_changes completed", num_changed_files=len(changed_files))
        return changed_files

    def check_for_deleted_files(self) -> list[str]:
        """
        Check for files that have been deleted since the last check.

        Returns:
            List[str]: List of deleted file IDs (paths)
        """
        structlog_logger.info(
            "check_for_deleted_files called", num_known_files=len(self.known_files)
        )
        deleted_files = []

        # Check each known file to see if it still exists
        structlog_logger.info("Checking known files for deletions")
        deleted_files = [
            file_path for file_path in self.known_files if not Path(file_path).exists()
        ]

        structlog_logger.info(
            "check_for_deleted_files completed", num_deleted_files=len(deleted_files)
        )
        return deleted_files

    def process_file(self, file: dict[str, Any]) -> None:
        """
        Process a single file for the RAG pipeline.

        Args:
            file: File information dictionary
        """
        file_path = file["id"]
        file_path_obj = Path(file["name"])
        file_name = file_path_obj.stem
        extension = file_path_obj.suffix
        mime_type = file["mimeType"]
        web_view_link = file["webViewLink"]

        structlog_logger.info("=" * 80)
        structlog_logger.info(
            "process_file called",
            file_name=file_name,
            extension=extension,
            file_path=file_path,
            mime_type=mime_type,
        )

        # Skip unsupported file types
        supported_mime_types = self.config.get("supported_mime_types", [])
        if not any(mime_type.startswith(t) for t in supported_mime_types):
            structlog_logger.warning(
                "Skipping unsupported file type",
                file_name=file_name,
                mime_type=mime_type,
                supported_types=supported_mime_types,
            )
            return

        # Get the file content
        structlog_logger.info("Step 1: Reading file content", file_path=file_path)
        file_content = self.get_file_content(file_path)
        if not file_content:
            structlog_logger.error(
                "Failed to read file content", file_name=file_name, file_path=file_path
            )
            return

        # Extract text from the file
        structlog_logger.info(
            "Step 2: Extracting text from file", file_name=file_name, mime_type=mime_type
        )
        text = extract_text_from_file(file_content, mime_type, file["name"], self.config)
        if not text:
            structlog_logger.warning(
                "No text could be extracted from file", file_name=file_name, file_path=file_path
            )
            return

        structlog_logger.info(
            "Text extracted successfully",
            file_name=file_name,
            text_length=len(text),
            text_preview=text[:100] + "..." if len(text) > 100 else text,
        )

        # Delete existing records (Agentic RAG doesn't handle updates yet)
        structlog_logger.info("Step 3a: Deleting existing records for file", file_id=file_path)
        delete_document_by_file_id(file_path)

        # Process the file with Agentic RAG pipeline
        structlog_logger.info(
            "Step 3b: Processing file with Agentic RAG pipeline",
            file_name=file_name,
            file_path=file_path,
        )
        success = process_file_with_agentic_rag_sync(
            text=text,
            file_id=file_path,
            file_title=file_name,
            file_url=web_view_link,
            mime_type=mime_type,
            use_rest_api=False,  # Try PostgreSQL first, fallback to REST
        )

        # Update the known files dictionary
        modified_time = file.get("modifiedTime")
        self.known_files[file_path] = modified_time if modified_time is not None else ""
        structlog_logger.info(
            "Updated known files registry", file_path=file_path, modified_time=modified_time
        )

        if success:
            structlog_logger.info(
                "File processed successfully", file_name=file_name, file_path=file_path
            )
        else:
            structlog_logger.error(
                "File processing failed", file_name=file_name, file_path=file_path
            )

    def watch_for_changes(self, interval_seconds: int = 60) -> None:
        """
        Watch for changes in the local directory at regular intervals.

        Args:
            interval_seconds: The interval in seconds between checks
        """
        structlog_logger.info("=" * 80)
        structlog_logger.info(
            "watch_for_changes called",
            watch_directory=self.watch_directory,
            interval_seconds=interval_seconds,
        )

        try:
            # Initial scan to build the known_files dictionary
            if not self.initialized:
                structlog_logger.info(
                    "Performing initial scan of files", watch_directory=self.watch_directory
                )
                # Get all files in the watched directory
                initial_files = self.get_changes()

                # Build the known_files dictionary - only store the modifiedTime
                for file in initial_files:
                    # Only store the modifiedTime to avoid processing all files
                    modified_time = file.get("modifiedTime")
                    self.known_files[file["id"]] = (
                        modified_time if modified_time is not None else ""
                    )

                structlog_logger.info(
                    "Initial scan completed", num_files_found=len(self.known_files)
                )
                self.initialized = True

            structlog_logger.info("Starting watch loop", interval_seconds=interval_seconds)
            while True:
                structlog_logger.info("=" * 80)
                structlog_logger.info("Starting new watch cycle")

                # Get changes since the last check
                structlog_logger.info("Step 1: Checking for changed files")
                changed_files = self.get_changes()

                # Check for deleted files
                structlog_logger.info("Step 2: Checking for deleted files")
                deleted_file_ids = self.check_for_deleted_files()

                # Process changed files
                if changed_files:
                    structlog_logger.info("Processing changed files", num_files=len(changed_files))
                    for file in changed_files:
                        self.process_file(file)
                else:
                    structlog_logger.info("No new or modified files found")

                # Process deleted files
                if deleted_file_ids:
                    structlog_logger.info(
                        "Processing deleted files", num_files=len(deleted_file_ids)
                    )
                    for file_id in deleted_file_ids:
                        structlog_logger.info("Deleting file from database", file_id=file_id)
                        # Delete from database
                        delete_document_by_file_id(file_id)
                        # Remove from known_files
                        del self.known_files[file_id]
                        structlog_logger.info("File deleted successfully", file_id=file_id)

                # Wait for the next check
                structlog_logger.info(
                    "Watch cycle completed, waiting for next cycle", wait_seconds=interval_seconds
                )
                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            structlog_logger.info("KeyboardInterrupt received, stopping Local File watcher")
        except Exception as e:
            structlog_logger.exception(
                "Error in Local File watcher", error=str(e), watch_directory=self.watch_directory
            )
