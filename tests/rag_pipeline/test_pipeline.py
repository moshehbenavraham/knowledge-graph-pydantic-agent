import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src directory to path to import the module
sys.path.append(str(Path(__file__).parent.parent.parent.resolve() / "src"))

# Try importing pipeline - skip tests if Google Drive dependencies not available
try:
    from rag_pipeline.pipeline import main

    PIPELINE_AVAILABLE = True
except ImportError:
    PIPELINE_AVAILABLE = False
    main = None

pytestmark = pytest.mark.skipif(
    not PIPELINE_AVAILABLE, reason="google-auth-oauthlib not installed (optional dependency)"
)


class TestPipeline:
    @patch("rag_pipeline.pipeline.argparse.ArgumentParser")
    @patch("rag_pipeline.pipeline.LocalFileWatcher")
    @patch("rag_pipeline.pipeline.GoogleDriveWatcher")
    def test_main_local_source(
        self, mock_google_drive_watcher, mock_local_file_watcher, mock_argument_parser
    ):
        # Configure ArgumentParser mock
        mock_args = MagicMock()
        mock_args.source = "local"
        mock_args.interval = 30
        mock_argument_parser.return_value.parse_args.return_value = mock_args

        # Configure LocalFileWatcher mock
        mock_local_watcher_instance = MagicMock()
        mock_local_file_watcher.return_value = mock_local_watcher_instance

        main()

        mock_argument_parser.assert_called_once()
        mock_local_file_watcher.assert_called_once()
        mock_local_watcher_instance.watch_for_changes.assert_called_once_with(30)
        mock_google_drive_watcher.assert_not_called()

    @patch("rag_pipeline.pipeline.argparse.ArgumentParser")
    @patch("rag_pipeline.pipeline.LocalFileWatcher")
    @patch("rag_pipeline.pipeline.GoogleDriveWatcher")
    def test_main_google_drive_source(
        self, mock_google_drive_watcher, mock_local_file_watcher, mock_argument_parser
    ):
        # Configure ArgumentParser mock
        mock_args = MagicMock()
        mock_args.source = "google_drive"
        mock_args.interval = 90
        mock_argument_parser.return_value.parse_args.return_value = mock_args

        # Configure GoogleDriveWatcher mock
        mock_google_watcher_instance = MagicMock()
        mock_google_drive_watcher.return_value = mock_google_watcher_instance

        main()

        mock_argument_parser.assert_called_once()
        mock_google_drive_watcher.assert_called_once()
        mock_google_watcher_instance.watch_for_changes.assert_called_once_with(90)
        mock_local_file_watcher.assert_not_called()

    @patch("rag_pipeline.pipeline.argparse.ArgumentParser")
    @patch("rag_pipeline.pipeline.LocalFileWatcher")
    @patch("rag_pipeline.pipeline.GoogleDriveWatcher")
    def test_main_default_interval(
        self, mock_google_drive_watcher, mock_local_file_watcher, mock_argument_parser
    ):
        # Configure ArgumentParser mock with default interval
        mock_args = MagicMock()
        mock_args.source = "local"
        mock_args.interval = 60  # Default value
        mock_argument_parser.return_value.parse_args.return_value = mock_args

        mock_local_watcher_instance = MagicMock()
        mock_local_file_watcher.return_value = mock_local_watcher_instance

        main()

        mock_local_watcher_instance.watch_for_changes.assert_called_once_with(60)

    @patch("rag_pipeline.pipeline.argparse.ArgumentParser")
    @patch("rag_pipeline.pipeline.LocalFileWatcher")
    def test_main_local_source_edge_cases(self, mock_local_file_watcher, mock_argument_parser):
        """Test local source with edge case intervals."""
        # Test with very short interval
        mock_args = MagicMock()
        mock_args.source = "local"
        mock_args.interval = 1
        mock_argument_parser.return_value.parse_args.return_value = mock_args

        mock_local_watcher_instance = MagicMock()
        mock_local_file_watcher.return_value = mock_local_watcher_instance

        main()

        mock_local_watcher_instance.watch_for_changes.assert_called_once_with(1)

    @patch("rag_pipeline.pipeline.argparse.ArgumentParser")
    @patch("rag_pipeline.pipeline.GoogleDriveWatcher")
    def test_main_google_drive_edge_cases(self, mock_google_drive_watcher, mock_argument_parser):
        """Test Google Drive source with edge case intervals."""
        # Test with very long interval
        mock_args = MagicMock()
        mock_args.source = "google_drive"
        mock_args.interval = 3600  # 1 hour
        mock_argument_parser.return_value.parse_args.return_value = mock_args

        mock_google_watcher_instance = MagicMock()
        mock_google_drive_watcher.return_value = mock_google_watcher_instance

        main()

        mock_google_watcher_instance.watch_for_changes.assert_called_once_with(3600)

    @patch("rag_pipeline.pipeline.argparse.ArgumentParser")
    @patch("rag_pipeline.pipeline.LocalFileWatcher")
    def test_main_local_watcher_initialization(self, mock_local_file_watcher, mock_argument_parser):
        """Test that LocalFileWatcher is properly initialized."""
        mock_args = MagicMock()
        mock_args.source = "local"
        mock_args.interval = 60
        mock_argument_parser.return_value.parse_args.return_value = mock_args

        mock_local_watcher_instance = MagicMock()
        mock_local_file_watcher.return_value = mock_local_watcher_instance

        main()

        # Verify watcher was initialized without arguments
        mock_local_file_watcher.assert_called_once_with()

    @patch("rag_pipeline.pipeline.argparse.ArgumentParser")
    @patch("rag_pipeline.pipeline.GoogleDriveWatcher")
    def test_main_google_drive_watcher_initialization(
        self, mock_google_drive_watcher, mock_argument_parser
    ):
        """Test that GoogleDriveWatcher is properly initialized."""
        mock_args = MagicMock()
        mock_args.source = "google_drive"
        mock_args.interval = 60
        mock_argument_parser.return_value.parse_args.return_value = mock_args

        mock_google_watcher_instance = MagicMock()
        mock_google_drive_watcher.return_value = mock_google_watcher_instance

        main()

        # Verify watcher was initialized without arguments
        mock_google_drive_watcher.assert_called_once_with()

    @patch.dict("sys.argv", ["pipeline.py", "--source", "local", "--interval", "120"])
    @patch("rag_pipeline.pipeline.LocalFileWatcher")
    def test_main_with_sys_argv(self, mock_local_file_watcher):
        """Test main function with actual sys.argv parsing."""
        mock_local_watcher_instance = MagicMock()
        mock_local_file_watcher.return_value = mock_local_watcher_instance

        main()

        mock_local_watcher_instance.watch_for_changes.assert_called_once_with(120)

    @patch.dict("sys.argv", ["pipeline.py", "--source", "google_drive"])
    @patch("rag_pipeline.pipeline.GoogleDriveWatcher")
    def test_main_google_drive_default_interval_real_argv(self, mock_google_drive_watcher):
        """Test Google Drive with default interval using real argv."""
        mock_google_watcher_instance = MagicMock()
        mock_google_drive_watcher.return_value = mock_google_watcher_instance

        main()

        # Should use default 60 second interval
        mock_google_watcher_instance.watch_for_changes.assert_called_once_with(60)
