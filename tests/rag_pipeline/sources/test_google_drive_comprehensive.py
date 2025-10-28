"""
Comprehensive tests for src/rag_pipeline/sources/google_drive.py

Covers:
- GoogleDriveWatcher initialization with various config paths
- load_config() with valid/invalid configs, date parsing
- save_last_check_time() success and error handling
- authenticate() with various credential states
- get_folder_contents() recursive traversal
- get_changes() with/without folder_id
- download_file() for regular and Google Workspace files
- process_file() for trashed, unsupported, and valid files
- check_for_deleted_files() finding trashed and missing files
- watch_for_changes() initial scan and continuous monitoring
"""

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

# Try importing Google Drive dependencies - skip tests if not available
try:
    from google.auth.exceptions import RefreshError

    from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    RefreshError = None
    GoogleDriveWatcher = None

pytestmark = pytest.mark.skipif(
    not GOOGLE_DRIVE_AVAILABLE, reason="google-auth-oauthlib not installed (optional dependency)"
)


@pytest.fixture
def temp_config_file():
    """Create a temporary config file."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        config = {
            "supported_mime_types": ["application/pdf", "text/plain"],
            "export_mime_types": {"application/vnd.google-apps.document": "text/plain"},
            "text_processing": {"default_chunk_size": 400, "default_chunk_overlap": 0},
            "last_check_time": "2024-01-01T12:00:00.000Z",
            "watch_folder_id": "test_folder_id",
        }
        json.dump(config, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def mock_google_apis():
    """Mock Google API modules."""
    with (
        patch("src.rag_pipeline.sources.google_drive.build") as mock_build,
        patch("src.rag_pipeline.sources.google_drive.Credentials") as mock_creds,
        patch("src.rag_pipeline.sources.google_drive.InstalledAppFlow") as mock_flow,
        patch("src.rag_pipeline.sources.google_drive.Request") as mock_request,
    ):
        yield {
            "build": mock_build,
            "credentials": mock_creds,
            "flow": mock_flow,
            "request": mock_request,
        }


class TestGoogleDriveWatcherInit:
    """Test GoogleDriveWatcher initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        with patch.object(GoogleDriveWatcher, "load_config"):
            watcher = GoogleDriveWatcher()

            assert watcher.credentials_path == "credentials.json"
            assert watcher.token_path == "token.json"
            assert watcher.folder_id is None
            assert watcher.service is None
            assert watcher.known_files == {}
            assert watcher.initialized is False

    def test_init_with_custom_paths(self):
        """Test initialization with custom paths."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        with patch.object(GoogleDriveWatcher, "load_config"):
            watcher = GoogleDriveWatcher(
                credentials_path="custom_creds.json",
                token_path="custom_token.json",
                folder_id="folder123",
            )

            assert watcher.credentials_path == "custom_creds.json"
            assert watcher.token_path == "custom_token.json"
            assert watcher.folder_id == "folder123"

    def test_init_with_config_path(self, temp_config_file):
        """Test initialization with custom config path."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        watcher = GoogleDriveWatcher(config_path=temp_config_file)

        assert watcher.config_path == temp_config_file
        assert watcher.folder_id == "test_folder_id"


class TestLoadConfig:
    """Test load_config() method."""

    def test_load_config_success(self, temp_config_file):
        """Test successful config loading."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        watcher = GoogleDriveWatcher(config_path=temp_config_file)

        assert watcher.config["supported_mime_types"] == ["application/pdf", "text/plain"]
        assert watcher.last_check_time == datetime(2024, 1, 1, 12, 0, 0)
        assert watcher.folder_id == "test_folder_id"

    def test_load_config_invalid_date_format(self):
        """Test config loading with invalid date format."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            config = {"last_check_time": "invalid-date"}
            json.dump(config, f)
            temp_path = f.name

        try:
            watcher = GoogleDriveWatcher(config_path=temp_path)

            # Should fall back to default date
            assert watcher.last_check_time == datetime(1970, 1, 1, 0, 0, 0)
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_load_config_file_not_found(self):
        """Test config loading when file doesn't exist."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        watcher = GoogleDriveWatcher(config_path="/nonexistent/config.json")

        # Should use default config
        assert "supported_mime_types" in watcher.config
        assert watcher.last_check_time == datetime(1970, 1, 1, 0, 0, 0)

    def test_load_config_json_decode_error(self):
        """Test config loading with invalid JSON."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            f.write("not valid json {")
            temp_path = f.name

        try:
            watcher = GoogleDriveWatcher(config_path=temp_path)

            # Should use default config
            assert "supported_mime_types" in watcher.config
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestSaveLastCheckTime:
    """Test save_last_check_time() method."""

    def test_save_last_check_time_success(self, temp_config_file):
        """Test successful save of last check time."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        watcher = GoogleDriveWatcher(config_path=temp_config_file)
        watcher.last_check_time = datetime(2024, 6, 15, 10, 30, 0)

        watcher.save_last_check_time()

        # Verify it was saved
        with open(temp_config_file) as f:
            saved_config = json.load(f)
            assert saved_config["last_check_time"] == "2024-06-15T10:30:00.000000Z"

    def test_save_last_check_time_error(self):
        """Test error handling when save fails."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        with patch.object(GoogleDriveWatcher, "load_config"):
            watcher = GoogleDriveWatcher()
            watcher.config_path = "/invalid/path/config.json"
            watcher.config = {}
            watcher.last_check_time = datetime.now(UTC)

            # Should not raise exception
            watcher.save_last_check_time()


class TestAuthenticate:
    """Test authenticate() method."""

    def test_authenticate_with_valid_token(self, mock_google_apis):
        """Test authentication with valid existing token."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        mock_creds = Mock()
        mock_creds.valid = True
        mock_google_apis["credentials"].from_authorized_user_info = Mock(return_value=mock_creds)

        mock_service = Mock()
        mock_google_apis["build"].return_value = mock_service

        token_data = {"token": "test_token", "refresh_token": "refresh"}

        with patch.object(GoogleDriveWatcher, "load_config"):
            with patch("builtins.open", mock_open(read_data=json.dumps(token_data))):
                with patch("pathlib.Path.exists", return_value=True):
                    watcher = GoogleDriveWatcher()
                    watcher.authenticate()

        assert watcher.service == mock_service
        mock_google_apis["build"].assert_called_once_with("drive", "v3", credentials=mock_creds)

    def test_authenticate_with_expired_token_refresh_success(self, mock_google_apis):
        """Test authentication with expired token that refreshes successfully."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        mock_creds = Mock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh_token"
        mock_creds.refresh = Mock()

        mock_google_apis["credentials"].from_authorized_user_info = Mock(return_value=mock_creds)
        mock_service = Mock()
        mock_google_apis["build"].return_value = mock_service

        token_data = {"token": "test_token"}

        with patch.object(GoogleDriveWatcher, "load_config"):
            with patch("builtins.open", mock_open(read_data=json.dumps(token_data))):
                with patch("pathlib.Path.exists", return_value=True):
                    watcher = GoogleDriveWatcher()
                    watcher.authenticate()

        mock_creds.refresh.assert_called_once()
        assert watcher.service == mock_service

    def test_authenticate_with_expired_token_refresh_fails(self, mock_google_apis):
        """Test authentication when token refresh fails."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        mock_creds = Mock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh_token"
        mock_creds.refresh = Mock(side_effect=RefreshError("Token expired"))

        mock_google_apis["credentials"].from_authorized_user_info = Mock(return_value=mock_creds)

        mock_new_creds = Mock()
        mock_new_creds.to_json = Mock(return_value='{"new": "token"}')

        mock_flow = Mock()
        mock_flow.run_local_server = Mock(return_value=mock_new_creds)
        mock_google_apis["flow"].from_client_secrets_file = Mock(return_value=mock_flow)

        mock_service = Mock()
        mock_google_apis["build"].return_value = mock_service

        token_data = {"token": "old_token"}

        with patch.object(GoogleDriveWatcher, "load_config"):
            with patch("builtins.open", mock_open(read_data=json.dumps(token_data))):
                with patch("pathlib.Path.exists", return_value=True):
                    watcher = GoogleDriveWatcher()
                    watcher.authenticate()

        # Should re-authenticate with flow
        mock_flow.run_local_server.assert_called_once()
        assert watcher.service == mock_service

    def test_authenticate_no_token_file(self, mock_google_apis):
        """Test authentication when no token file exists."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        mock_new_creds = Mock()
        mock_new_creds.to_json = Mock(return_value='{"new": "token"}')

        mock_flow = Mock()
        mock_flow.run_local_server = Mock(return_value=mock_new_creds)
        mock_google_apis["flow"].from_client_secrets_file = Mock(return_value=mock_flow)

        mock_service = Mock()
        mock_google_apis["build"].return_value = mock_service

        with patch.object(GoogleDriveWatcher, "load_config"):
            with patch("pathlib.Path.exists", return_value=False):
                with patch("builtins.open", mock_open()):
                    watcher = GoogleDriveWatcher()
                    watcher.authenticate()

        mock_flow.run_local_server.assert_called_once()
        assert watcher.service == mock_service


class TestGetFolderContents:
    """Test get_folder_contents() method."""

    def test_get_folder_contents_no_service(self):
        """Test get_folder_contents when service is not initialized."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        with patch.object(GoogleDriveWatcher, "load_config"):
            with patch.object(GoogleDriveWatcher, "authenticate") as mock_auth:
                watcher = GoogleDriveWatcher()
                watcher.service = None

                # authenticate() will be called but service stays None
                mock_auth.return_value = None

                result = watcher.get_folder_contents("folder_id", "2024-01-01T00:00:00.000Z")

        assert result == []

    def test_get_folder_contents_with_files(self):
        """Test get_folder_contents returns files."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        mock_service = Mock()
        mock_files_list = Mock()
        mock_files_list.execute = Mock(
            return_value={
                "files": [
                    {"id": "file1", "name": "doc1.pdf", "mimeType": "application/pdf"},
                    {"id": "file2", "name": "doc2.txt", "mimeType": "text/plain"},
                ]
            }
        )
        mock_service.files().list = Mock(return_value=mock_files_list)

        with patch.object(GoogleDriveWatcher, "load_config"):
            watcher = GoogleDriveWatcher()
            watcher.service = mock_service

            result = watcher.get_folder_contents("folder_id", "2024-01-01T00:00:00.000Z")

        assert len(result) == 2
        assert result[0]["id"] == "file1"

    def test_get_folder_contents_recursive(self):
        """Test get_folder_contents recursively traverses subfolders."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        mock_service = Mock()

        # First call: returns files and has subfolders
        files_response = {"files": [{"id": "file1", "name": "doc.pdf"}]}

        # Second call for subfolders: finds one subfolder
        folder_response = {"files": [{"id": "subfolder1"}]}

        # Third call for subfolder contents
        subfolder_files_response = {"files": [{"id": "file2", "name": "subdoc.txt"}]}

        # Fourth call for subfolder's subfolders (none)
        empty_folder_response = {"files": []}

        mock_execute = Mock(
            side_effect=[
                files_response,
                folder_response,
                subfolder_files_response,
                empty_folder_response,
            ]
        )

        mock_service.files().list().execute = mock_execute
        mock_service.files().list = Mock(return_value=Mock(execute=mock_execute))

        with patch.object(GoogleDriveWatcher, "load_config"):
            watcher = GoogleDriveWatcher()
            watcher.service = mock_service

            result = watcher.get_folder_contents("folder_id", "2024-01-01T00:00:00.000Z")

        # Should have files from main folder + subfolder
        assert len(result) == 2


class TestGetChanges:
    """Test get_changes() method."""

    def test_get_changes_no_service(self):
        """Test get_changes when service is not initialized."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        with patch.object(GoogleDriveWatcher, "load_config"):
            with patch.object(GoogleDriveWatcher, "authenticate") as mock_auth:
                watcher = GoogleDriveWatcher()
                watcher.service = None
                mock_auth.return_value = None

                result = watcher.get_changes()

        assert result == []

    def test_get_changes_with_folder_id(self):
        """Test get_changes with specific folder_id."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        with patch.object(GoogleDriveWatcher, "load_config"):
            with patch.object(GoogleDriveWatcher, "get_folder_contents") as mock_get_folder:
                with patch.object(GoogleDriveWatcher, "save_last_check_time"):
                    mock_get_folder.return_value = [{"id": "file1"}]

                    watcher = GoogleDriveWatcher()
                    watcher.service = Mock()
                    watcher.folder_id = "test_folder"
                    watcher.last_check_time = datetime(2024, 1, 1)

                    result = watcher.get_changes()

        assert len(result) == 1
        mock_get_folder.assert_called_once()

    def test_get_changes_without_folder_id(self):
        """Test get_changes for all drive files."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        mock_service = Mock()
        mock_list = Mock()
        mock_list.execute = Mock(return_value={"files": [{"id": "file1"}, {"id": "file2"}]})
        mock_service.files().list = Mock(return_value=mock_list)

        with patch.object(GoogleDriveWatcher, "load_config"):
            with patch.object(GoogleDriveWatcher, "save_last_check_time"):
                watcher = GoogleDriveWatcher()
                watcher.service = mock_service
                watcher.folder_id = None
                watcher.last_check_time = datetime(2024, 1, 1)

                result = watcher.get_changes()

        assert len(result) == 2

    def test_get_changes_updates_last_check_time(self):
        """Test get_changes updates last_check_time."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        mock_service = Mock()
        mock_service.files().list().execute = Mock(return_value={"files": []})

        with patch.object(GoogleDriveWatcher, "load_config"):
            with patch.object(GoogleDriveWatcher, "save_last_check_time") as mock_save:
                watcher = GoogleDriveWatcher()
                watcher.service = mock_service
                watcher.folder_id = None
                watcher.last_check_time = datetime(2024, 1, 1)

                old_time = watcher.last_check_time
                watcher.get_changes()

                assert watcher.last_check_time > old_time
                mock_save.assert_called_once()


class TestDownloadFile:
    """Test download_file() method."""

    def test_download_file_regular_file(self, mock_google_apis):
        """Test downloading a regular file."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        mock_service = Mock()
        mock_request = Mock()
        mock_service.files().get_media = Mock(return_value=mock_request)

        # Mock MediaIoBaseDownload
        file_content = b"test file content"
        with patch(
            "src.rag_pipeline.sources.google_drive.MediaIoBaseDownload"
        ) as mock_downloader_class:
            mock_downloader = Mock()
            mock_downloader.next_chunk = Mock(return_value=(Mock(), True))
            mock_downloader_class.return_value = mock_downloader

            with patch.object(GoogleDriveWatcher, "load_config"):
                watcher = GoogleDriveWatcher()
                watcher.service = mock_service
                watcher.config = {"export_mime_types": {}}

                # Mock BytesIO to return our content
                with patch("io.BytesIO") as mock_bytesio:
                    mock_buffer = Mock()
                    mock_buffer.read = Mock(return_value=file_content)
                    mock_bytesio.return_value = mock_buffer

                    result = watcher.download_file("file_id", "application/pdf")

        assert result == file_content

    def test_download_file_google_workspace_export(self):
        """Test downloading and exporting a Google Workspace file."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        mock_service = Mock()
        mock_request = Mock()
        mock_service.files().export_media = Mock(return_value=mock_request)

        file_content = b"exported content"
        with patch(
            "src.rag_pipeline.sources.google_drive.MediaIoBaseDownload"
        ) as mock_downloader_class:
            mock_downloader = Mock()
            mock_downloader.next_chunk = Mock(return_value=(Mock(), True))
            mock_downloader_class.return_value = mock_downloader

            with patch.object(GoogleDriveWatcher, "load_config"):
                watcher = GoogleDriveWatcher()
                watcher.service = mock_service
                watcher.config = {
                    "export_mime_types": {"application/vnd.google-apps.document": "text/plain"}
                }

                with patch("io.BytesIO") as mock_bytesio:
                    mock_buffer = Mock()
                    mock_buffer.read = Mock(return_value=file_content)
                    mock_bytesio.return_value = mock_buffer

                    result = watcher.download_file(
                        "file_id", "application/vnd.google-apps.document"
                    )

        assert result == file_content
        mock_service.files().export_media.assert_called_once()

    def test_download_file_multiple_chunks(self):
        """Test downloading file with multiple chunks."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        mock_service = Mock()
        mock_request = Mock()
        mock_service.files().get_media = Mock(return_value=mock_request)

        with patch(
            "src.rag_pipeline.sources.google_drive.MediaIoBaseDownload"
        ) as mock_downloader_class:
            mock_downloader = Mock()
            # Simulate 3 chunks
            mock_downloader.next_chunk = Mock(
                side_effect=[(Mock(), False), (Mock(), False), (Mock(), True)]
            )
            mock_downloader_class.return_value = mock_downloader

            with patch.object(GoogleDriveWatcher, "load_config"):
                watcher = GoogleDriveWatcher()
                watcher.service = mock_service
                watcher.config = {"export_mime_types": {}}

                with patch("io.BytesIO") as mock_bytesio:
                    mock_buffer = Mock()
                    mock_buffer.read = Mock(return_value=b"content")
                    mock_bytesio.return_value = mock_buffer

                    result = watcher.download_file("file_id", "application/pdf")

        assert mock_downloader.next_chunk.call_count == 3

    def test_download_file_error(self):
        """Test download_file error handling."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        mock_service = Mock()
        mock_service.files().get_media = Mock(side_effect=Exception("Download failed"))

        with patch.object(GoogleDriveWatcher, "load_config"):
            watcher = GoogleDriveWatcher()
            watcher.service = mock_service
            watcher.config = {"export_mime_types": {}}

            result = watcher.download_file("file_id", "application/pdf")

        assert result is None


class TestProcessFile:
    """Test process_file() method."""

    def test_process_file_trashed(self):
        """Test processing a trashed file."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        file = {"id": "file1", "name": "doc.pdf", "mimeType": "application/pdf", "trashed": True}

        with patch(
            "src.rag_pipeline.sources.google_drive.delete_document_by_file_id"
        ) as mock_delete:
            with patch.object(GoogleDriveWatcher, "load_config"):
                watcher = GoogleDriveWatcher()
                watcher.known_files = {"file1": "2024-01-01"}

                watcher.process_file(file)

        mock_delete.assert_called_once_with("file1")
        assert "file1" not in watcher.known_files

    def test_process_file_unsupported_type(self):
        """Test processing file with unsupported MIME type."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        file = {"id": "file1", "name": "image.png", "mimeType": "image/png", "trashed": False}

        with patch.object(GoogleDriveWatcher, "load_config"):
            with patch.object(GoogleDriveWatcher, "download_file") as mock_download:
                watcher = GoogleDriveWatcher()
                watcher.config = {"supported_mime_types": ["application/pdf", "text/plain"]}

                watcher.process_file(file)

        # Should not attempt download
        mock_download.assert_not_called()

    def test_process_file_download_fails(self):
        """Test processing file when download fails."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        file = {"id": "file1", "name": "doc.pdf", "mimeType": "application/pdf", "trashed": False}

        with patch.object(GoogleDriveWatcher, "load_config"):
            with patch.object(GoogleDriveWatcher, "download_file", return_value=None):
                watcher = GoogleDriveWatcher()
                watcher.config = {"supported_mime_types": ["application/pdf"]}

                watcher.process_file(file)

        # Should not update known_files
        assert "file1" not in watcher.known_files

    def test_process_file_extract_text_fails(self):
        """Test processing file when text extraction fails."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        file = {"id": "file1", "name": "doc.pdf", "mimeType": "application/pdf", "trashed": False}

        with patch.object(GoogleDriveWatcher, "load_config"):
            with patch.object(GoogleDriveWatcher, "download_file", return_value=b"content"):
                with patch(
                    "src.rag_pipeline.sources.google_drive.extract_text_from_file", return_value=""
                ):
                    watcher = GoogleDriveWatcher()
                    watcher.config = {"supported_mime_types": ["application/pdf"]}

                    watcher.process_file(file)

        # Should not update known_files
        assert "file1" not in watcher.known_files

    def test_process_file_success(self):
        """Test successful file processing."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        file = {
            "id": "file1",
            "name": "doc.pdf",
            "mimeType": "application/pdf",
            "webViewLink": "https://drive.google.com/file/file1",
            "modifiedTime": "2024-01-01T12:00:00.000Z",
            "trashed": False,
        }

        with patch.object(GoogleDriveWatcher, "load_config"):
            with patch.object(GoogleDriveWatcher, "download_file", return_value=b"content"):
                with patch(
                    "src.rag_pipeline.sources.google_drive.extract_text_from_file",
                    return_value="Extracted text",
                ):
                    with patch(
                        "src.rag_pipeline.sources.google_drive.process_file_for_rag",
                        return_value=True,
                    ):
                        watcher = GoogleDriveWatcher()
                        watcher.config = {"supported_mime_types": ["application/pdf"]}

                        watcher.process_file(file)

        assert "file1" in watcher.known_files
        assert watcher.known_files["file1"] == "2024-01-01T12:00:00.000Z"


class TestCheckForDeletedFiles:
    """Test check_for_deleted_files() method."""

    def test_check_for_deleted_files_no_service(self):
        """Test check_for_deleted_files when service is None."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        with patch.object(GoogleDriveWatcher, "load_config"):
            with patch.object(GoogleDriveWatcher, "authenticate"):
                watcher = GoogleDriveWatcher()
                watcher.service = None
                watcher.known_files = {"file1": "2024-01-01"}

                result = watcher.check_for_deleted_files()

        assert result == []

    def test_check_for_deleted_files_no_known_files(self):
        """Test check_for_deleted_files with empty known_files."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        with patch.object(GoogleDriveWatcher, "load_config"):
            watcher = GoogleDriveWatcher()
            watcher.service = Mock()
            watcher.known_files = {}

            result = watcher.check_for_deleted_files()

        assert result == []

    def test_check_for_deleted_files_trashed(self):
        """Test check_for_deleted_files finds trashed files."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        mock_service = Mock()
        mock_service.files().get().execute = Mock(
            return_value={"trashed": True, "name": "trashed_file.pdf"}
        )

        with patch.object(GoogleDriveWatcher, "load_config"):
            watcher = GoogleDriveWatcher()
            watcher.service = mock_service
            watcher.known_files = {"file1": "2024-01-01"}

            result = watcher.check_for_deleted_files()

        assert "file1" in result

    def test_check_for_deleted_files_not_found(self):
        """Test check_for_deleted_files finds missing files."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        mock_service = Mock()
        mock_service.files().get().execute = Mock(side_effect=Exception("File not found: 404"))

        with patch.object(GoogleDriveWatcher, "load_config"):
            watcher = GoogleDriveWatcher()
            watcher.service = mock_service
            watcher.known_files = {"file1": "2024-01-01"}

            result = watcher.check_for_deleted_files()

        assert "file1" in result

    def test_check_for_deleted_files_other_error(self):
        """Test check_for_deleted_files handles other errors gracefully."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        mock_service = Mock()
        mock_service.files().get().execute = Mock(side_effect=Exception("Network error"))

        with patch.object(GoogleDriveWatcher, "load_config"):
            watcher = GoogleDriveWatcher()
            watcher.service = mock_service
            watcher.known_files = {"file1": "2024-01-01"}

            result = watcher.check_for_deleted_files()

        # Should not include file (only 404 and trashed files)
        assert result == []


class TestWatchForChanges:
    """Test watch_for_changes() method."""

    def test_watch_for_changes_no_service(self):
        """Test watch_for_changes when authentication fails."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        with patch.object(GoogleDriveWatcher, "load_config"):
            with patch.object(GoogleDriveWatcher, "authenticate"):
                watcher = GoogleDriveWatcher()
                watcher.service = None

                watcher.watch_for_changes()

        # Should exit gracefully

    def test_watch_for_changes_initial_scan(self):
        """Test watch_for_changes performs initial scan."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        mock_service = Mock()
        mock_service.files().list().execute = Mock(
            return_value={
                "files": [
                    {"id": "file1", "modifiedTime": "2024-01-01T00:00:00.000Z", "trashed": False},
                    {"id": "file2", "modifiedTime": "2024-01-02T00:00:00.000Z", "trashed": False},
                ]
            }
        )

        with patch.object(GoogleDriveWatcher, "load_config"):
            with patch.object(GoogleDriveWatcher, "get_changes", return_value=[]):
                with patch.object(GoogleDriveWatcher, "check_for_deleted_files", return_value=[]):
                    with patch(
                        "time.sleep", side_effect=KeyboardInterrupt
                    ):  # Exit after one iteration
                        watcher = GoogleDriveWatcher()
                        watcher.service = mock_service
                        watcher.folder_id = None

                        try:
                            watcher.watch_for_changes()
                        except KeyboardInterrupt:
                            pass

        # Should have populated known_files
        assert len(watcher.known_files) == 2

    def test_watch_for_changes_processes_changed_files(self):
        """Test watch_for_changes processes changed files."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        changed_file = {
            "id": "file1",
            "name": "doc.pdf",
            "mimeType": "application/pdf",
            "modifiedTime": "2024-01-01T00:00:00.000Z",
            "trashed": False,
        }

        with patch.object(GoogleDriveWatcher, "load_config"):
            with patch.object(GoogleDriveWatcher, "authenticate"):
                with patch.object(GoogleDriveWatcher, "get_changes", return_value=[changed_file]):
                    with patch.object(GoogleDriveWatcher, "process_file") as mock_process:
                        with patch.object(
                            GoogleDriveWatcher, "check_for_deleted_files", return_value=[]
                        ):
                            with patch("time.sleep", side_effect=KeyboardInterrupt):
                                watcher = GoogleDriveWatcher()
                                watcher.service = Mock()
                                watcher.initialized = True

                                try:
                                    watcher.watch_for_changes()
                                except KeyboardInterrupt:
                                    pass

        mock_process.assert_called_once_with(changed_file)

    def test_watch_for_changes_handles_deleted_files(self):
        """Test watch_for_changes handles deleted files."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        with patch.object(GoogleDriveWatcher, "load_config"):
            with patch.object(GoogleDriveWatcher, "authenticate"):
                with patch.object(GoogleDriveWatcher, "get_changes", return_value=[]):
                    with patch.object(
                        GoogleDriveWatcher, "check_for_deleted_files", return_value=["file1"]
                    ):
                        with patch(
                            "src.rag_pipeline.sources.google_drive.delete_document_by_file_id"
                        ) as mock_delete:
                            with patch("time.sleep", side_effect=KeyboardInterrupt):
                                watcher = GoogleDriveWatcher()
                                watcher.service = Mock()
                                watcher.initialized = True
                                watcher.known_files = {"file1": "2024-01-01"}

                                try:
                                    watcher.watch_for_changes()
                                except KeyboardInterrupt:
                                    pass

        mock_delete.assert_called_once_with("file1")
        assert "file1" not in watcher.known_files

    def test_watch_for_changes_exception_handling(self):
        """Test watch_for_changes handles exceptions."""
        from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher

        with patch.object(GoogleDriveWatcher, "load_config"):
            with patch.object(GoogleDriveWatcher, "authenticate"):
                with patch.object(
                    GoogleDriveWatcher, "get_changes", side_effect=Exception("API error")
                ):
                    watcher = GoogleDriveWatcher()
                    watcher.service = Mock()
                    watcher.initialized = True

                    with pytest.raises(Exception, match="API error"):
                        watcher.watch_for_changes()
