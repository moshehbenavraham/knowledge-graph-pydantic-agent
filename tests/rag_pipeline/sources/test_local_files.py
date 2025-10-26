import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# Add src directory to path to import the module
sys.path.append(str(Path(__file__).parent.parent.parent.parent.resolve()))
from src.rag_pipeline.sources.local_files import LocalFileWatcher


class TestLocalFileWatcher:
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        # Mock external dependencies
        with (
            patch("src.rag_pipeline.sources.local_files.os") as mock_os,
            patch("src.rag_pipeline.sources.local_files.json") as mock_json,
            patch("src.rag_pipeline.sources.local_files.time.sleep") as mock_sleep,
            patch("src.rag_pipeline.sources.local_files.datetime") as mock_datetime,
            patch("src.rag_pipeline.sources.local_files.mimetypes") as mock_mimetypes,
            patch(
                "src.rag_pipeline.sources.local_files.extract_text_from_file"
            ) as mock_extract_text_from_file,
            patch(
                "src.rag_pipeline.sources.local_files.process_file_for_rag"
            ) as mock_process_file_for_rag,
            patch(
                "src.rag_pipeline.sources.local_files.delete_document_by_file_id"
            ) as mock_delete_document_by_file_id,
        ):

            # Configure os mocks
            mock_os.path.exists.return_value = True  # Assume files exist by default
            mock_os.path.join.side_effect = os.path.join  # Use real join
            mock_os.path.dirname.side_effect = os.path.dirname  # Use real dirname
            mock_os.path.abspath.side_effect = os.path.abspath  # Use real abspath
            mock_os.makedirs.return_value = None
            mock_os.remove.return_value = None
            mock_os.stat.return_value = MagicMock(
                st_mtime=datetime(2025, 1, 1, 9, 0, 0).timestamp(),
                st_ctime=datetime(2025, 1, 1, 8, 0, 0).timestamp(),
            )
            mock_os.path.splitext.side_effect = os.path.splitext
            mock_os.path.relpath.side_effect = os.path.relpath

            # Configure json mocks
            mock_json.load.return_value = {
                "watch_directory": "data",
                "last_check_time": "1970-01-01T00:00:00.000Z",
                "supported_mime_types": ["application/pdf", "text/plain"],
                "tabular_mime_types": ["text/csv"],
                "text_processing": {"default_chunk_size": 400, "default_chunk_overlap": 0},
            }
            mock_json.dump.return_value = None

            # Configure datetime mock
            mock_datetime.now.return_value = datetime(2025, 1, 1, 10, 0, 0)
            mock_datetime.strptime.side_effect = datetime.strptime
            mock_datetime.fromtimestamp.side_effect = datetime.fromtimestamp

            # Configure mimetypes mock
            mock_mimetypes.guess_type.return_value = ("text/plain", None)

            # Configure common functions mocks
            mock_extract_text_from_file.return_value = "extracted text"
            mock_process_file_for_rag.return_value = True
            mock_delete_document_by_file_id.return_value = None

            self.mock_os = mock_os
            self.mock_json = mock_json
            self.mock_sleep = mock_sleep
            self.mock_datetime = mock_datetime
            self.mock_mimetypes = mock_mimetypes
            self.mock_extract_text_from_file = mock_extract_text_from_file
            self.mock_process_file_for_rag = mock_process_file_for_rag
            self.mock_delete_document_by_file_id = mock_delete_document_by_file_id

            yield

    def test_init_and_load_config(self):
        watcher = LocalFileWatcher(config_path="/tmp/config.json")  # nosec B108 - test usage
        assert watcher.watch_directory.endswith("data")
        assert watcher.last_check_time == datetime(1970, 1, 1, 0, 0, 0)
        self.mock_json.load.assert_called_once()
        self.mock_os.makedirs.assert_called_once()

    def test_save_last_check_time(self):
        watcher = LocalFileWatcher(config_path="/tmp/config.json")  # nosec B108 - test usage
        watcher.last_check_time = datetime(2025, 1, 1, 10, 0, 0)
        watcher.save_last_check_time()
        self.mock_json.dump.assert_called_once()
        assert (
            self.mock_json.dump.call_args[0][0]["last_check_time"] == "2025-01-01T10:00:00.000000Z"
        )

    def test_get_mime_type(self):
        watcher = LocalFileWatcher()
        assert (
            watcher.get_mime_type("test.xlsx")
            == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        assert watcher.get_mime_type("test.csv") == "text/csv"
        self.mock_mimetypes.guess_type.return_value = ("application/json", None)
        assert watcher.get_mime_type("test.json") == "application/json"
        self.mock_mimetypes.guess_type.return_value = (None, None)
        assert watcher.get_mime_type("test.xyz") == "text/plain"

    @patch("builtins.open", new_callable=MagicMock)
    def test_get_file_content_success(self, mock_open):
        watcher = LocalFileWatcher()
        mock_file = MagicMock()
        mock_file.read.return_value = b"file content"
        mock_open.return_value.__enter__.return_value = mock_file

        result = watcher.get_file_content("/path/to/file.txt")
        mock_open.assert_called_once_with("/path/to/file.txt", "rb")
        assert result == b"file content"

    @patch("builtins.open", side_effect=Exception("Read error"))
    def test_get_file_content_failure(self, mock_open):
        watcher = LocalFileWatcher()
        with patch("builtins.print") as mock_print:
            result = watcher.get_file_content("/path/to/file.txt")
            mock_print.assert_called_once_with("Error reading file /path/to/file.txt: Read error")
            assert result is None

    def test_get_changes_new_and_modified_files(self):
        watcher = LocalFileWatcher()
        watcher.watch_directory = "/tmp/test_watch"  # nosec B108 - test usage
        self.mock_os.walk.return_value = [
            ("/tmp/test_watch", [], ["file1.txt", "file2.pdf"]),  # nosec B108 - test usage
            ("/tmp/test_watch/subdir", [], ["file3.csv"]),  # nosec B108 - test usage
        ]

        # Simulate file1.txt as new, file2.pdf as modified, file3.csv as new
        self.mock_os.stat.side_effect = [
            MagicMock(
                st_mtime=datetime(2025, 1, 1, 9, 30, 0).timestamp(),
                st_ctime=datetime(2025, 1, 1, 8, 30, 0).timestamp(),
            ),  # file1.txt (new)
            MagicMock(
                st_mtime=datetime(2025, 1, 1, 9, 45, 0).timestamp(),
                st_ctime=datetime(2025, 1, 1, 7, 0, 0).timestamp(),
            ),  # file2.pdf (modified)
            MagicMock(
                st_mtime=datetime(2025, 1, 1, 9, 50, 0).timestamp(),
                st_ctime=datetime(2025, 1, 1, 8, 50, 0).timestamp(),
            ),  # file3.csv (new)
        ]
        watcher.last_check_time = datetime(2025, 1, 1, 9, 0, 0)  # Files modified after this time
        watcher.known_files = {
            "/tmp/test_watch/file2.pdf": datetime(
                2025, 1, 1, 9, 0, 0
            ).isoformat()  # nosec B108 - test usage
        }  # Only file2 is known

        with patch.object(watcher, "save_last_check_time") as mock_save_last_check_time:
            results = watcher.get_changes()

            assert len(results) == 3
            assert any(f["name"] == "file1.txt" for f in results)
            assert any(f["name"] == "file2.pdf" for f in results)
            assert any(f["name"] == "file3.csv" for f in results)
            mock_save_last_check_time.assert_called_once()
            assert watcher.last_check_time == datetime(2025, 1, 1, 10, 0, 0)

    def test_check_for_deleted_files(self):
        watcher = LocalFileWatcher()
        watcher.known_files = {"/path/to/existing.txt": "time1", "/path/to/deleted.txt": "time2"}
        self.mock_os.path.exists.side_effect = lambda x: x == "/path/to/existing.txt"

        deleted = watcher.check_for_deleted_files()
        assert deleted == ["/path/to/deleted.txt"]

    def test_process_file_success(self):
        watcher = LocalFileWatcher()
        watcher.get_file_content = MagicMock(return_value=b"file content")

        file_info = {
            "id": "/path/to/file.txt",
            "name": "file.txt",
            "mimeType": "text/plain",
            "webViewLink": "link",
        }
        watcher.process_file(file_info)

        watcher.get_file_content.assert_called_once_with("/path/to/file.txt")
        self.mock_extract_text_from_file.assert_called_once_with(
            b"file content", "text/plain", "file.txt", watcher.config
        )
        self.mock_process_file_for_rag.assert_called_once_with(
            b"file content",
            "extracted text",
            "/path/to/file.txt",
            "link",
            "file.txt",
            "text/plain",
            watcher.config,
        )
        assert watcher.known_files["/path/to/file.txt"] == file_info.get("modifiedTime")

    def test_process_file_unsupported_mime_type(self):
        watcher = LocalFileWatcher()
        watcher.get_file_content = MagicMock(return_value=b"file content")

        file_info = {"id": "/path/to/file.zip", "name": "file.zip", "mimeType": "application/zip"}
        watcher.process_file(file_info)

        watcher.get_file_content.assert_called_once_with("/path/to/file.zip")
        self.mock_extract_text_from_file.assert_not_called()
        self.mock_process_file_for_rag.assert_not_called()

    @patch("src.rag_pipeline.sources.local_files.LocalFileWatcher.get_changes")
    @patch("src.rag_pipeline.sources.local_files.LocalFileWatcher.check_for_deleted_files")
    @patch("src.rag_pipeline.sources.local_files.LocalFileWatcher.process_file")
    def test_watch_for_changes_initial_scan_and_loop(
        self, mock_process_file, mock_check_for_deleted_files, mock_get_changes
    ):
        watcher = LocalFileWatcher(watch_directory="/tmp/test_watch")  # nosec B108 - test usage

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
                "id": "/tmp/test_watch/file1.txt",  # nosec B108 - test usage
                "name": "file1.txt",
                "mimeType": "text/plain",
                "modifiedTime": "2025-01-01T09:00:00.000Z",
            },
            {
                "id": "/tmp/test_watch/file2.txt",  # nosec B108 - test usage
                "name": "file2.txt",
                "mimeType": "text/plain",
                "modifiedTime": "2025-01-01T09:00:00.000Z",
            },
        ]
        mock_get_changes.side_effect = [
            mock_initial_files,  # Initial scan
            [
                {
                    "id": "/tmp/test_watch/new_file.txt",  # nosec B108 - test usage
                    "name": "new_file.txt",
                    "mimeType": "text/plain",
                    "modifiedTime": "2025-01-01T10:00:00.000Z",
                }
            ],  # New file
            [],  # No more changes
            [],  # Extra loop with no changes before stopping
            KeyboardInterrupt,  # Stop the loop
        ]
        mock_check_for_deleted_files.side_effect = [
            [],  # No deleted files initially
            ["/tmp/test_watch/file1.txt"],  # One deleted file  # nosec B108 - test usage
            [],  # No more deleted files
        ]

        watcher.watch_for_changes(interval_seconds=1)

        # Verify initial scan populated known_files
        assert "/tmp/test_watch/file1.txt" in tracking_known_files.added  # nosec B108 - test usage
        assert "/tmp/test_watch/file2.txt" in tracking_known_files.added  # nosec B108 - test usage
        assert "/tmp/test_watch/file2.txt" in watcher.known_files  # nosec B108 - test usage

        # Verify subsequent loop iterations
        mock_get_changes.assert_has_calls([call(), call(), call()])  # Called three times
        mock_check_for_deleted_files.assert_has_calls(
            [call(), call(), call()]
        )  # Called three times
        mock_process_file.assert_called_once_with(
            {
                "id": "/tmp/test_watch/new_file.txt",  # nosec B108 - test usage
                "name": "new_file.txt",
                "mimeType": "text/plain",
                "modifiedTime": "2025-01-01T10:00:00.000Z",
            }
        )
        self.mock_delete_document_by_file_id.assert_called_once_with(
            "/tmp/test_watch/file1.txt"
        )  # nosec B108 - test usage
        assert "/tmp/test_watch/file1.txt" not in watcher.known_files  # nosec B108 - test usage
        self.mock_sleep.assert_called_with(1)
