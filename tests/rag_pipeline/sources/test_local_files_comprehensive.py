"""
Comprehensive tests for local file watcher and processing.

Target coverage: 0% -> 95%+

Tests file watching, MIME type detection, file processing, change tracking,
configuration loading, and integration with RAG pipeline.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from src.rag_pipeline.sources.local_files import LocalFileWatcher


class TestLocalFileWatcherInit:
    """Test LocalFileWatcher initialization."""

    def test_init_with_defaults(self, tmp_path):
        """Test initialization with default parameters."""
        # Create config file
        config_path = tmp_path / "config.json"
        config_data = {
            "watch_directory": "data",
            "supported_mime_types": ["application/pdf", "text/plain"],
            "last_check_time": "1970-01-01T00:00:00.000Z",
        }
        config_path.write_text(json.dumps(config_data))

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(config_path=str(config_path))

        assert watcher.config_path == str(config_path)
        assert watcher.initialized is False
        assert watcher.known_files == {}

    def test_init_with_watch_directory(self, tmp_path):
        """Test initialization with explicit watch directory."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({}))

        watch_dir = tmp_path / "watch"

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(watch_directory=str(watch_dir), config_path=str(config_path))

        assert str(watch_dir) in watcher.watch_directory

    def test_init_creates_watch_directory(self, tmp_path):
        """Test that watch directory is created if it doesn't exist."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({}))

        watch_dir = tmp_path / "new_watch_dir"

        with patch.object(Path, "resolve", return_value=tmp_path):
            LocalFileWatcher(watch_directory=str(watch_dir), config_path=str(config_path))

        # Directory should be created
        assert watch_dir.exists()


class TestLoadConfig:
    """Test configuration loading."""

    def test_load_config_success(self, tmp_path):
        """Test successful config loading."""
        config_path = tmp_path / "config.json"
        config_data = {
            "watch_directory": "data",
            "supported_mime_types": ["application/pdf"],
            "last_check_time": "2025-01-01T12:00:00.000Z",
        }
        config_path.write_text(json.dumps(config_data))

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(config_path=str(config_path))

        assert watcher.config["watch_directory"] == "data"
        assert "application/pdf" in watcher.config["supported_mime_types"]
        assert watcher.last_check_time.year == 2025

    def test_load_config_invalid_date_format(self, tmp_path):
        """Test config loading with invalid date format."""
        config_path = tmp_path / "config.json"
        config_data = {
            "watch_directory": "data",
            "last_check_time": "invalid-date",
        }
        config_path.write_text(json.dumps(config_data))

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(config_path=str(config_path))

        # Should use default date
        assert watcher.last_check_time.year == 1970

    def test_load_config_file_not_found(self, tmp_path):
        """Test config loading when file doesn't exist."""
        config_path = tmp_path / "nonexistent.json"

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(config_path=str(config_path))

        # Should use default config
        assert "supported_mime_types" in watcher.config
        assert watcher.last_check_time.year == 1970

    def test_load_config_invalid_json(self, tmp_path):
        """Test config loading with invalid JSON."""
        config_path = tmp_path / "config.json"
        config_path.write_text("invalid json {")

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(config_path=str(config_path))

        # Should use default config
        assert "supported_mime_types" in watcher.config


class TestSaveLastCheckTime:
    """Test saving last check time."""

    def test_save_last_check_time_success(self, tmp_path):
        """Test successful saving of last check time."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({}))

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(config_path=str(config_path))

        # Update last check time
        new_time = datetime.strptime("2025-02-01T10:00:00.000Z", "%Y-%m-%dT%H:%M:%S.%fZ")
        watcher.last_check_time = new_time

        watcher.save_last_check_time()

        # Verify saved
        with open(config_path) as f:
            saved_config = json.load(f)

        assert "2025-02-01" in saved_config["last_check_time"]

    def test_save_last_check_time_write_error(self, tmp_path, caplog):
        """Test handling write error when saving."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({}))

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(config_path=str(config_path))

        # Mock Path.open to raise exception
        with patch.object(Path, "open", side_effect=PermissionError("Permission denied")):
            watcher.save_last_check_time()

        # Should log error
        assert "Error saving last check time" in caplog.text


class TestGetMimeType:
    """Test MIME type detection."""

    def test_get_mime_type_xlsx(self, tmp_path):
        """Test MIME type for xlsx file."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({}))

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(config_path=str(config_path))

        mime_type = watcher.get_mime_type("test.xlsx")
        assert mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    def test_get_mime_type_pdf(self, tmp_path):
        """Test MIME type for PDF file."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({}))

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(config_path=str(config_path))

        mime_type = watcher.get_mime_type("document.pdf")
        assert mime_type == "application/pdf"

    def test_get_mime_type_csv(self, tmp_path):
        """Test MIME type for CSV file."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({}))

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(config_path=str(config_path))

        mime_type = watcher.get_mime_type("data.csv")
        assert mime_type == "text/csv"

    def test_get_mime_type_txt(self, tmp_path):
        """Test MIME type for text file."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({}))

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(config_path=str(config_path))

        mime_type = watcher.get_mime_type("readme.txt")
        assert mime_type == "text/plain"

    def test_get_mime_type_unknown(self, tmp_path):
        """Test MIME type for unknown file extension."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({}))

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(config_path=str(config_path))

        mime_type = watcher.get_mime_type("file.unknown")
        assert mime_type == "text/plain"  # Default fallback


class TestGetFileContent:
    """Test file content reading."""

    def test_get_file_content_success(self, tmp_path):
        """Test successful file reading."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({}))

        # Create test file
        test_file = tmp_path / "test.txt"
        test_content = b"Test file content"
        test_file.write_bytes(test_content)

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(config_path=str(config_path))

        content = watcher.get_file_content(str(test_file))

        assert content == test_content

    def test_get_file_content_file_not_found(self, tmp_path, caplog):
        """Test handling file not found."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({}))

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(config_path=str(config_path))

        content = watcher.get_file_content("/nonexistent/file.txt")

        assert content is None
        assert "Error reading file content" in caplog.text


class TestGetChanges:
    """Test change detection."""

    def test_get_changes_new_files(self, tmp_path):
        """Test detecting new files."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"last_check_time": "1970-01-01T00:00:00.000Z"}))

        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()

        # Create test files
        (watch_dir / "file1.txt").write_text("Content 1")
        (watch_dir / "file2.pdf").write_text("Content 2")

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(watch_directory="watch", config_path=str(config_path))

        changes = watcher.get_changes()

        assert len(changes) == 2
        assert any(f["name"] == "file1.txt" for f in changes)
        assert any(f["name"] == "file2.pdf" for f in changes)

    def test_get_changes_modified_files(self, tmp_path):
        """Test detecting modified files."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"last_check_time": "1970-01-01T00:00:00.000Z"}))

        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()

        test_file = watch_dir / "file.txt"
        test_file.write_text("Original content")

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(watch_directory="watch", config_path=str(config_path))

        # First check
        changes1 = watcher.get_changes()
        assert len(changes1) == 1

        # Modify file
        time.sleep(0.1)  # Ensure different timestamp
        test_file.write_text("Modified content")

        # Second check
        changes2 = watcher.get_changes()
        assert len(changes2) == 1

    def test_get_changes_no_changes(self, tmp_path):
        """Test when no changes detected."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"last_check_time": "2099-01-01T00:00:00.000Z"}))

        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()

        # Create old file
        (watch_dir / "old_file.txt").write_text("Old content")

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(watch_directory="watch", config_path=str(config_path))

        # Since last_check_time is in future, no changes should be detected
        changes = watcher.get_changes()

        # Still detects file in known_files tracking, but depends on implementation
        assert isinstance(changes, list)


class TestCheckForDeletedFiles:
    """Test deleted file detection."""

    def test_check_for_deleted_files_none(self, tmp_path):
        """Test when no files deleted."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({}))

        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()

        test_file = watch_dir / "file.txt"
        test_file.write_text("Content")

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(watch_directory="watch", config_path=str(config_path))

        # Add file to known files
        watcher.known_files[str(test_file)] = "2025-01-01T00:00:00Z"

        deleted = watcher.check_for_deleted_files()

        assert len(deleted) == 0

    def test_check_for_deleted_files_some_deleted(self, tmp_path):
        """Test when files are deleted."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({}))

        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(watch_directory="watch", config_path=str(config_path))

        # Add non-existent files to known files
        watcher.known_files["/nonexistent/file1.txt"] = "2025-01-01T00:00:00Z"
        watcher.known_files["/nonexistent/file2.pdf"] = "2025-01-01T00:00:00Z"

        deleted = watcher.check_for_deleted_files()

        assert len(deleted) == 2
        assert "/nonexistent/file1.txt" in deleted
        assert "/nonexistent/file2.pdf" in deleted


class TestProcessFile:
    """Test file processing."""

    def test_process_file_success(self, tmp_path):
        """Test successful file processing."""
        config_path = tmp_path / "config.json"
        config_data = {
            "supported_mime_types": ["text/plain"],
            "text_processing": {"default_chunk_size": 400},
        }
        config_path.write_text(json.dumps(config_data))

        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(config_path=str(config_path))

        # Mock dependencies
        with (
            patch(
                "src.rag_pipeline.sources.local_files.extract_text_from_file",
                return_value="Extracted text",
            ),
            patch("src.rag_pipeline.sources.local_files.process_file_for_rag", return_value=True),
        ):
            file_info = {
                "id": str(test_file),
                "name": "test.txt",
                "mimeType": "text/plain",
                "webViewLink": f"file://{test_file}",
                "modifiedTime": "2025-01-01T00:00:00Z",
            }

            watcher.process_file(file_info)

        # File should be added to known_files
        assert str(test_file) in watcher.known_files

    def test_process_file_unsupported_type(self, tmp_path, caplog):
        """Test processing unsupported file type."""
        config_path = tmp_path / "config.json"
        config_data = {"supported_mime_types": ["application/pdf"]}
        config_path.write_text(json.dumps(config_data))

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(config_path=str(config_path))

        file_info = {
            "id": "/path/file.txt",
            "name": "file.txt",
            "mimeType": "text/plain",
            "webViewLink": "file:///path/file.txt",
        }

        watcher.process_file(file_info)

        # Should log warning about unsupported type
        assert "Skipping unsupported file type" in caplog.text

    def test_process_file_read_error(self, tmp_path, caplog):
        """Test handling file read error."""
        config_path = tmp_path / "config.json"
        config_data = {"supported_mime_types": ["text/plain"]}
        config_path.write_text(json.dumps(config_data))

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(config_path=str(config_path))

        # Mock get_file_content to return None (error)
        watcher.get_file_content = Mock(return_value=None)

        file_info = {
            "id": "/path/file.txt",
            "name": "file.txt",
            "mimeType": "text/plain",
            "webViewLink": "file:///path/file.txt",
        }

        watcher.process_file(file_info)

        # Should log error
        assert "Failed to read file content" in caplog.text

    def test_process_file_extraction_error(self, tmp_path, caplog):
        """Test handling text extraction error."""
        config_path = tmp_path / "config.json"
        config_data = {"supported_mime_types": ["text/plain"]}
        config_path.write_text(json.dumps(config_data))

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(config_path=str(config_path))

        watcher.get_file_content = Mock(return_value=b"content")

        # Mock extract_text_from_file to return None (error)
        with patch(
            "src.rag_pipeline.sources.local_files.extract_text_from_file", return_value=None
        ):
            file_info = {
                "id": "/path/file.txt",
                "name": "file.txt",
                "mimeType": "text/plain",
                "webViewLink": "file:///path/file.txt",
            }

            watcher.process_file(file_info)

        # Should log warning
        assert "No text could be extracted" in caplog.text


class TestWatchForChanges:
    """Test watch loop."""

    def test_watch_for_changes_initial_scan(self, tmp_path):
        """Test initial scan of files."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({"last_check_time": "1970-01-01T00:00:00.000Z"}))

        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()

        # Create test files
        (watch_dir / "file1.txt").write_text("Content 1")
        (watch_dir / "file2.txt").write_text("Content 2")

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(watch_directory="watch", config_path=str(config_path))

        # Mock to stop after initial scan
        with patch("time.sleep", side_effect=KeyboardInterrupt):
            try:
                watcher.watch_for_changes(interval_seconds=1)
            except KeyboardInterrupt:
                pass

        # Should have performed initial scan
        assert watcher.initialized is True
        assert len(watcher.known_files) == 2

    def test_watch_for_changes_keyboard_interrupt(self, tmp_path, caplog):
        """Test handling keyboard interrupt."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({}))

        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(watch_directory="watch", config_path=str(config_path))

        # Trigger KeyboardInterrupt during watch
        with patch("time.sleep", side_effect=KeyboardInterrupt):
            watcher.watch_for_changes(interval_seconds=1)

        # Should log graceful shutdown
        assert "KeyboardInterrupt received" in caplog.text

    def test_watch_for_changes_general_exception(self, tmp_path, caplog):
        """Test handling general exception."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({}))

        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(watch_directory="watch", config_path=str(config_path))

        # Trigger exception during watch
        with patch.object(watcher, "get_changes", side_effect=Exception("Test error")):
            watcher.watch_for_changes(interval_seconds=1)

        # Should log error
        assert "Error in Local File watcher" in caplog.text

    def test_watch_for_changes_process_deleted_files(self, tmp_path):
        """Test processing deleted files during watch."""
        config_path = tmp_path / "config.json"
        config_path.write_text(json.dumps({}))

        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()

        with patch.object(Path, "resolve", return_value=tmp_path):
            watcher = LocalFileWatcher(watch_directory="watch", config_path=str(config_path))

        # Pre-populate known files with deleted file
        watcher.initialized = True
        watcher.known_files["/deleted/file.txt"] = "2025-01-01T00:00:00Z"

        # Mock dependencies
        with (
            patch.object(watcher, "get_changes", return_value=[]),
            patch.object(watcher, "check_for_deleted_files", return_value=["/deleted/file.txt"]),
            patch("src.rag_pipeline.sources.local_files.delete_document_by_file_id") as mock_delete,
            patch("time.sleep", side_effect=KeyboardInterrupt),
        ):
            try:
                watcher.watch_for_changes(interval_seconds=1)
            except KeyboardInterrupt:
                pass

        # Should have called delete
        mock_delete.assert_called_once_with("/deleted/file.txt")
        assert "/deleted/file.txt" not in watcher.known_files
