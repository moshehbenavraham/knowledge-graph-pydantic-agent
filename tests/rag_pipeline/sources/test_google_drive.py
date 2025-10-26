import io
import json
import os
import sys
from datetime import UTC, datetime, timezone
from pathlib import Path
from unittest.mock import ANY, MagicMock, call, patch

import pytest

# Try importing Google Drive dependencies - skip tests if not available
try:
    from google.auth.exceptions import RefreshError
    from google.oauth2.credentials import Credentials

    # Add src directory to path to import the module
    sys.path.append(str(Path(__file__).parent.parent.parent.parent.resolve() / "src"))
    from rag_pipeline.sources.google_drive import SCOPES, GoogleDriveWatcher

    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    # Create dummy classes to prevent import errors
    SCOPES = None
    GoogleDriveWatcher = None

pytestmark = pytest.mark.skipif(
    not GOOGLE_DRIVE_AVAILABLE, reason="google-auth-oauthlib not installed (optional dependency)"
)


class TestGoogleDriveWatcher:
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        # Mock external dependencies
        with (
            patch("rag_pipeline.sources.google_drive.build") as mock_build,
            patch("rag_pipeline.sources.google_drive.MediaIoBaseDownload") as mock_media_download,
            patch("rag_pipeline.sources.google_drive.Credentials") as mock_credentials,
            patch("rag_pipeline.sources.google_drive.InstalledAppFlow") as mock_installed_app_flow,
            patch("rag_pipeline.sources.google_drive.Request") as mock_request,
            patch("rag_pipeline.sources.google_drive.os") as mock_os,
            patch("rag_pipeline.sources.google_drive.json") as mock_json,
            patch("rag_pipeline.sources.google_drive.time.sleep") as mock_sleep,
            patch("rag_pipeline.sources.google_drive.datetime") as mock_datetime,
            patch(
                "rag_pipeline.sources.google_drive.extract_text_from_file"
            ) as mock_extract_text_from_file,
            patch(
                "rag_pipeline.sources.google_drive.process_file_for_rag"
            ) as mock_process_file_for_rag,
            patch(
                "rag_pipeline.sources.google_drive.delete_document_by_file_id"
            ) as mock_delete_document_by_file_id,
        ):

            # Configure os mocks
            mock_os.path.exists.return_value = False  # Assume token.json does not exist by default
            mock_os.path.join.side_effect = os.path.join  # Use real join
            mock_os.path.dirname.side_effect = os.path.dirname  # Use real dirname
            mock_os.path.abspath.side_effect = os.path.abspath  # Use real abspath
            mock_os.makedirs.return_value = None
            mock_os.remove.return_value = None

            # Configure json mocks
            mock_json.load.return_value = {
                "watch_folder_id": "test_folder_id",
                "last_check_time": "1970-01-01T00:00:00.000Z",
                "supported_mime_types": ["application/pdf", "text/plain"],
                "export_mime_types": {"application/vnd.google-apps.document": "text/plain"},
                "text_processing": {"default_chunk_size": 400, "default_chunk_overlap": 0},
            }
            mock_json.dump.return_value = None

            # Configure datetime mock
            mock_datetime.now.return_value = datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)
            mock_datetime.strptime.side_effect = datetime.strptime
            mock_datetime.fromtimestamp.side_effect = datetime.fromtimestamp
            mock_datetime.timezone = timezone  # Ensure timezone is accessible

            # Configure Google API mocks
            mock_service = MagicMock()
            mock_build.return_value = mock_service
            mock_files = MagicMock()
            mock_service.files.return_value = mock_files
            mock_list = MagicMock()
            mock_files.list.return_value = mock_list
            mock_list.execute.return_value = {"files": []}  # Default no files
            mock_get_media = MagicMock()
            mock_files.get_media.return_value = mock_get_media
            mock_export_media = MagicMock()
            mock_files.export_media.return_value = mock_export_media

            mock_flow_instance = MagicMock()
            mock_installed_app_flow.from_client_secrets_file.return_value = mock_flow_instance
            mock_flow_instance.run_local_server.return_value = MagicMock(
                spec=Credentials, valid=True, expired=False
            )

            # Configure common functions mocks
            mock_extract_text_from_file.return_value = "extracted text"
            mock_process_file_for_rag.return_value = True
            mock_delete_document_by_file_id.return_value = None

            self.mock_build = mock_build
            self.mock_media_download = mock_media_download
            self.mock_credentials = mock_credentials
            self.mock_installed_app_flow = mock_installed_app_flow
            self.mock_request = mock_request
            self.mock_os = mock_os
            self.mock_json = mock_json
            self.mock_sleep = mock_sleep
            self.mock_datetime = mock_datetime
            self.mock_extract_text_from_file = mock_extract_text_from_file
            self.mock_process_file_for_rag = mock_process_file_for_rag
            self.mock_delete_document_by_file_id = mock_delete_document_by_file_id
            self.mock_service = mock_service
            self.mock_files = mock_files
            self.mock_list = mock_list
            self.mock_get_media = mock_get_media
            self.mock_export_media = mock_export_media

            yield

    def test_init_and_load_config(self):
        watcher = GoogleDriveWatcher(config_path="/tmp/config.json")  # nosec B108 - test usage
        assert watcher.folder_id == "test_folder_id"
        assert watcher.last_check_time == datetime(1970, 1, 1, 0, 0, 0)
        self.mock_json.load.assert_called_once()

    def test_save_last_check_time(self):
        watcher = GoogleDriveWatcher(config_path="/tmp/config.json")  # nosec B108 - test usage
        watcher.last_check_time = datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)
        watcher.save_last_check_time()
        self.mock_json.dump.assert_called_once()
        assert (
            self.mock_json.dump.call_args[0][0]["last_check_time"] == "2025-01-01T10:00:00.000000Z"
        )

    @patch("rag_pipeline.sources.google_drive.open", new_callable=MagicMock)
    def test_authenticate_no_token(self, mock_open):
        self.mock_os.path.exists.return_value = False  # token.json does not exist
        watcher = GoogleDriveWatcher()
        watcher.authenticate()
        self.mock_installed_app_flow.from_client_secrets_file.assert_called_once_with(
            "credentials.json", SCOPES
        )
        self.mock_installed_app_flow.from_client_secrets_file.return_value.run_local_server.assert_called_once_with(
            port=0
        )
        self.mock_build.assert_called_once()
        mock_open.assert_called_once_with("token.json", "w")

    @patch("rag_pipeline.sources.google_drive.open", new_callable=MagicMock)
    def test_authenticate_valid_token(self, mock_open):
        self.mock_os.path.exists.return_value = True  # token.json exists
        mock_token_file = MagicMock()
        mock_token_file.read.return_value = json.dumps({"token": "valid_token"})
        mock_open.return_value.__enter__.return_value = mock_token_file

        mock_creds_instance = MagicMock(spec=Credentials, valid=True, expired=False)
        self.mock_credentials.from_authorized_user_info.return_value = mock_creds_instance

        watcher = GoogleDriveWatcher()
        watcher.authenticate()
        self.mock_credentials.from_authorized_user_info.assert_called_once()
        self.mock_installed_app_flow.from_client_secrets_file.assert_not_called()
        self.mock_build.assert_called_once()

    @patch("rag_pipeline.sources.google_drive.open", new_callable=MagicMock)
    def test_authenticate_expired_token_refresh_success(self, mock_open):
        self.mock_os.path.exists.return_value = True  # token.json exists
        mock_token_file = MagicMock()
        mock_token_file.read.return_value = json.dumps({"token": "expired_token"})
        mock_open.return_value.__enter__.return_value = mock_token_file

        mock_creds_instance = MagicMock(
            spec=Credentials,
            valid=False,
            expired=True,
            refresh_token="refresh_token",  # nosec B106 - test data
        )
        mock_creds_instance.refresh.return_value = None  # Simulate successful refresh
        self.mock_credentials.from_authorized_user_info.return_value = mock_creds_instance

        watcher = GoogleDriveWatcher()
        watcher.authenticate()
        mock_creds_instance.refresh.assert_called_once_with(self.mock_request.return_value)
        self.mock_installed_app_flow.from_client_secrets_file.assert_not_called()
        self.mock_build.assert_called_once()

    @patch("rag_pipeline.sources.google_drive.open", new_callable=MagicMock)
    def test_authenticate_expired_token_refresh_failure(self, mock_open):
        self.mock_os.path.exists.return_value = True  # token.json exists
        mock_token_file = MagicMock()
        mock_token_file.read.return_value = json.dumps({"token": "expired_token"})
        mock_open.return_value.__enter__.return_value = mock_token_file

        mock_creds_instance = MagicMock(
            spec=Credentials,
            valid=False,
            expired=True,
            refresh_token="refresh_token",  # nosec B106 - test data
        )
        mock_creds_instance.refresh.side_effect = RefreshError  # Simulate refresh failure
        self.mock_credentials.from_authorized_user_info.return_value = mock_creds_instance

        watcher = GoogleDriveWatcher()
        watcher.authenticate()
        mock_creds_instance.refresh.assert_called_once_with(self.mock_request.return_value)
        self.mock_installed_app_flow.from_client_secrets_file.assert_called_once_with(
            "credentials.json", SCOPES
        )
        self.mock_installed_app_flow.from_client_secrets_file.return_value.run_local_server.assert_called_once_with(
            port=0
        )
        self.mock_build.assert_called_once()

    def test_get_folder_contents_recursive(self):
        watcher = GoogleDriveWatcher(folder_id="root_folder")
        watcher.service = self.mock_service  # Set the mocked service

        # Mock files().list() for root folder
        mock_list_root_files = MagicMock()
        mock_list_root_files.execute.return_value = {
            "files": [
                {
                    "id": "file1",
                    "name": "File1",
                    "mimeType": "text/plain",
                    "modifiedTime": "2025-01-01T09:00:00.000Z",
                },
                {
                    "id": "subfolder1",
                    "name": "Subfolder1",
                    "mimeType": "application/vnd.google-apps.folder",
                },
            ]
        }
        # Mock files().list() for subfolder content
        mock_list_subfolder_files = MagicMock()
        mock_list_subfolder_files.execute.return_value = {
            "files": [
                {
                    "id": "file2",
                    "name": "File2",
                    "mimeType": "text/plain",
                    "modifiedTime": "2025-01-01T09:30:00.000Z",
                }
            ]
        }
        # Mock files().list() for subfolder identification
        mock_list_subfolder_id = MagicMock()
        mock_list_subfolder_id.execute.return_value = {"files": [{"id": "subfolder1"}]}

        self.mock_files.list.side_effect = [
            mock_list_root_files,  # First call for root files
            mock_list_subfolder_id,  # Second call for subfolder identification
            mock_list_subfolder_files,  # Third call for subfolder content
        ]

        time_str = "2025-01-01T08:00:00.000Z"
        result = watcher.get_folder_contents("root_folder", time_str)

        assert len(result) == 2
        assert any(f["id"] == "file1" for f in result)
        assert any(f["id"] == "file2" for f in result)
        self.mock_files.list.assert_has_calls(
            [
                call(
                    q=f"(modifiedTime > '{time_str}' or createdTime > '{time_str}') and 'root_folder' in parents",
                    pageSize=100,
                    fields=ANY,
                ),
                call(
                    q="'root_folder' in parents and mimeType = 'application/vnd.google-apps.folder'",
                    pageSize=100,
                    fields=ANY,
                ),
                call(
                    q=f"(modifiedTime > '{time_str}' or createdTime > '{time_str}') and 'subfolder1' in parents",
                    pageSize=100,
                    fields=ANY,
                ),
            ]
        )

    def test_get_changes_with_folder_id(self):
        watcher = GoogleDriveWatcher(folder_id="test_folder_id")
        watcher.service = self.mock_service  # Set the mocked service
        watcher.last_check_time = datetime(2025, 1, 1, 9, 0, 0, tzinfo=UTC)

        mock_get_folder_contents_result = [
            {
                "id": "file1",
                "name": "File1",
                "mimeType": "text/plain",
                "modifiedTime": "2025-01-01T10:00:00.000Z",
            }
        ]
        with (
            patch.object(
                watcher, "get_folder_contents", return_value=mock_get_folder_contents_result
            ) as mock_get_folder_contents,
            patch.object(watcher, "save_last_check_time") as mock_save_last_check_time,
        ):
            result = watcher.get_changes()
            mock_get_folder_contents.assert_called_once_with(
                "test_folder_id", "2025-01-01T09:00:00.000000Z"
            )
            assert len(result) == 1
            assert result[0]["id"] == "file1"
            mock_save_last_check_time.assert_called_once()
            assert watcher.last_check_time == datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)

    def test_get_changes_no_folder_id(self):
        watcher = GoogleDriveWatcher(folder_id=None)
        watcher.service = self.mock_service  # Set the mocked service
        watcher.last_check_time = datetime(2025, 1, 1, 9, 0, 0, tzinfo=UTC)

        mock_list_all_files = MagicMock()
        mock_list_all_files.execute.return_value = {
            "files": [
                {
                    "id": "file2",
                    "name": "File2",
                    "mimeType": "text/plain",
                    "modifiedTime": "2025-01-01T10:00:00.000Z",
                }
            ]
        }
        self.mock_files.list.return_value = mock_list_all_files

        with patch.object(watcher, "save_last_check_time") as mock_save_last_check_time:
            result = watcher.get_changes()
            self.mock_files.list.assert_called_once_with(
                q="modifiedTime > '2025-01-01T09:00:00.000000Z' or createdTime > '2025-01-01T09:00:00.000000Z'",
                pageSize=100,
                fields=ANY,
            )
            assert len(result) == 1
            assert result[0]["id"] == "file2"
            mock_save_last_check_time.assert_called_once()
            assert watcher.last_check_time == datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC)

    @patch("googleapiclient.http.MediaIoBaseDownload")
    def test_download_file_regular(self, mock_media_download):
        watcher = GoogleDriveWatcher()
        watcher.service = self.mock_service

        mock_file_content_io = io.BytesIO(b"downloaded content")
        mock_media_download_instance = MagicMock()
        mock_media_download_instance.next_chunk.side_effect = [(None, False), (None, True)]
        mock_media_download_instance.next_chunk.return_value = (None, True)  # Ensure it stops
        mock_media_download.return_value = mock_media_download_instance

        with patch("io.BytesIO", return_value=mock_file_content_io):
            result = watcher.download_file("file_id_1", "text/plain")
            self.mock_files.get_media.assert_called_once_with(fileId="file_id_1")
            assert result == b"downloaded content"

    @patch("googleapiclient.http.MediaIoBaseDownload")
    def test_download_file_google_workspace(self, mock_media_download):
        watcher = GoogleDriveWatcher()
        watcher.service = self.mock_service

        mock_file_content_io = io.BytesIO(b"exported content")
        mock_media_download_instance = MagicMock()
        mock_media_download_instance.next_chunk.side_effect = [(None, False), (None, True)]
        mock_media_download_instance.next_chunk.return_value = (None, True)  # Ensure it stops
        mock_media_download.return_value = mock_media_download_instance

        with patch("io.BytesIO", return_value=mock_file_content_io):
            result = watcher.download_file("file_id_2", "application/vnd.google-apps.document")
            self.mock_files.export_media.assert_called_once_with(
                fileId="file_id_2", mimeType="text/plain"
            )
            assert result == b"exported content"

    def test_process_file_trashed(self):
        watcher = GoogleDriveWatcher()
        file_info = {"id": "file_id", "name": "File", "mimeType": "text/plain", "trashed": True}
        watcher.known_files = {"file_id": "some_time"}  # Add to known files

        watcher.process_file(file_info)
        self.mock_delete_document_by_file_id.assert_called_once_with("file_id")
        assert "file_id" not in watcher.known_files

    def test_process_file_unsupported_mime_type(self):
        watcher = GoogleDriveWatcher()
        file_info = {"id": "file_id", "name": "File", "mimeType": "application/zip"}

        watcher.process_file(file_info)
        self.mock_extract_text_from_file.assert_not_called()
        self.mock_process_file_for_rag.assert_not_called()

    def test_process_file_success(self):
        watcher = GoogleDriveWatcher()
        watcher.download_file = MagicMock(return_value=b"file content")

        file_info = {
            "id": "file_id",
            "name": "File",
            "mimeType": "text/plain",
            "webViewLink": "link",
        }
        watcher.process_file(file_info)

        watcher.download_file.assert_called_once_with("file_id", "text/plain")
        self.mock_extract_text_from_file.assert_called_once_with(
            b"file content", "text/plain", "File", watcher.config
        )
        self.mock_process_file_for_rag.assert_called_once_with(
            b"file content",
            "extracted text",
            "file_id",
            "link",
            "File",
            "text/plain",
            watcher.config,
        )
        assert watcher.known_files["file_id"] == file_info.get("modifiedTime")

    def test_check_for_deleted_files(self):
        watcher = GoogleDriveWatcher()
        watcher.service = self.mock_service
        watcher.known_files = {"file1": "time1", "file2": "time2"}

        # Mock get() for file1 (trashed)
        mock_get_file1 = MagicMock()
        mock_get_file1.execute.return_value = {"trashed": True, "name": "File1"}
        # Mock get() for file2 (not found)
        mock_get_file2 = MagicMock()
        mock_get_file2.execute.side_effect = Exception("File not found")

        self.mock_files.get.side_effect = [mock_get_file1, mock_get_file2]

        deleted_files = watcher.check_for_deleted_files()
        assert "file1" in deleted_files
        assert "file2" in deleted_files
        self.mock_files.get.assert_has_calls(
            [
                call(fileId="file1", fields="trashed,name"),
                call(fileId="file2", fields="trashed,name"),
            ]
        )

    @patch("rag_pipeline.sources.google_drive.GoogleDriveWatcher.get_changes")
    @patch("rag_pipeline.sources.google_drive.GoogleDriveWatcher.check_for_deleted_files")
    @patch("rag_pipeline.sources.google_drive.GoogleDriveWatcher.process_file")
    def test_watch_for_changes_initial_scan_and_loop(
        self, mock_process_file, mock_check_for_deleted_files, mock_get_changes
    ):
        watcher = GoogleDriveWatcher(folder_id="test_folder_id")
        watcher.service = self.mock_service

        class TrackingDict(dict):
            def __init__(self):
                super().__init__()
                self.added: set[str] = set()
                self.removed: set[str] = set()

            def __setitem__(self, key, value):  # type: ignore[override]
                self.added.add(key)
                super().__setitem__(key, value)

            def __delitem__(self, key):  # type: ignore[override]
                self.removed.add(key)
                super().__delitem__(key)

        tracking_known_files = TrackingDict()
        watcher.known_files = tracking_known_files

        # Mock initial scan files
        mock_initial_files = [
            {
                "id": "init_file1",
                "name": "InitFile1",
                "mimeType": "text/plain",
                "modifiedTime": "2025-01-01T09:00:00.000Z",
            },
            {
                "id": "init_file2",
                "name": "InitFile2",
                "mimeType": "text/plain",
                "modifiedTime": "2025-01-01T09:00:00.000Z",
                "trashed": True,
            },
        ]
        with patch.object(watcher, "get_folder_contents", return_value=mock_initial_files):
            # Mock subsequent changes
            mock_get_changes.side_effect = [
                [
                    {
                        "id": "new_file",
                        "name": "NewFile",
                        "mimeType": "text/plain",
                        "modifiedTime": "2025-01-01T10:00:00.000Z",
                    }
                ],
                [],  # No more changes
                KeyboardInterrupt,  # Stop the loop
            ]
            mock_check_for_deleted_files.side_effect = [
                [],  # No deleted files initially
                ["deleted_file"],  # One deleted file
                [],  # No more deleted files
            ]

            watcher.watch_for_changes(interval_seconds=1)

            # Verify initial scan
            assert "init_file1" in tracking_known_files.added
            assert (
                "init_file2" not in tracking_known_files.added
            )  # Trashed file should not be added
            assert "init_file1" in watcher.known_files

            # Verify subsequent loop iterations
            mock_get_changes.assert_has_calls(
                [call(), call()]
            )  # Called twice before KeyboardInterrupt
            mock_check_for_deleted_files.assert_has_calls([call(), call()])  # Called twice
            mock_process_file.assert_called_once_with(
                {
                    "id": "new_file",
                    "name": "NewFile",
                    "mimeType": "text/plain",
                    "modifiedTime": "2025-01-01T10:00:00.000Z",
                }
            )
            self.mock_delete_document_by_file_id.assert_called_once_with("deleted_file")
            assert "deleted_file" not in watcher.known_files
            self.mock_sleep.assert_called_with(1)
