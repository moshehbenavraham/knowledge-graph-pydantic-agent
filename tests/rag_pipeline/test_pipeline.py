from unittest.mock import MagicMock, patch

import pytest

from src.rag_pipeline.pipeline import main


class TestPipeline:
    @patch("src.rag_pipeline.pipeline.argparse.ArgumentParser")
    @patch("src.rag_pipeline.pipeline.LocalFileWatcher")
    @patch("src.rag_pipeline.pipeline.GoogleDriveWatcher")
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

    @patch("src.rag_pipeline.pipeline.argparse.ArgumentParser")
    @patch("src.rag_pipeline.pipeline.LocalFileWatcher")
    @patch("src.rag_pipeline.pipeline.GoogleDriveWatcher")
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

    @patch("src.rag_pipeline.pipeline.argparse.ArgumentParser")
    @patch("src.rag_pipeline.pipeline.LocalFileWatcher")
    @patch("src.rag_pipeline.pipeline.GoogleDriveWatcher")
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

    @patch("src.rag_pipeline.pipeline.argparse.ArgumentParser")
    @patch("src.rag_pipeline.pipeline.LocalFileWatcher")
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

    @patch("src.rag_pipeline.pipeline.argparse.ArgumentParser")
    @patch("src.rag_pipeline.pipeline.GoogleDriveWatcher")
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

    @patch("src.rag_pipeline.pipeline.argparse.ArgumentParser")
    @patch("src.rag_pipeline.pipeline.LocalFileWatcher")
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

    @patch("src.rag_pipeline.pipeline.argparse.ArgumentParser")
    @patch("src.rag_pipeline.pipeline.GoogleDriveWatcher")
    @patch("src.rag_pipeline.pipeline.settings")
    def test_main_google_drive_watcher_initialization(
        self, mock_settings, mock_google_drive_watcher, mock_argument_parser
    ):
        """Test that GoogleDriveWatcher is properly initialized."""
        mock_args = MagicMock()
        mock_args.source = "google_drive"
        mock_args.interval = 60
        mock_argument_parser.return_value.parse_args.return_value = mock_args

        # Mock settings attributes
        mock_settings.google_drive_credentials_path = "config/google_credentials.json"
        mock_settings.google_drive_folder_id = "test_folder_id"

        mock_google_watcher_instance = MagicMock()
        mock_google_drive_watcher.return_value = mock_google_watcher_instance

        main()

        # Verify watcher was initialized with correct arguments
        mock_google_drive_watcher.assert_called_once_with(
            credentials_path="config/google_credentials.json",
            token_path="config/google_token.json",
            folder_id="test_folder_id",
        )

    @patch("sys.argv", ["pipeline.py", "--source", "local", "--interval", "120"])
    @patch("src.rag_pipeline.pipeline.LocalFileWatcher")
    def test_main_with_sys_argv(self, mock_local_file_watcher):
        """Test main function with actual sys.argv parsing."""
        mock_local_watcher_instance = MagicMock()
        mock_local_file_watcher.return_value = mock_local_watcher_instance

        main()

        mock_local_watcher_instance.watch_for_changes.assert_called_once_with(120)

    @patch("sys.argv", ["pipeline.py", "--source", "google_drive"])
    @patch("src.rag_pipeline.pipeline.GoogleDriveWatcher")
    def test_main_google_drive_default_interval_real_argv(self, mock_google_drive_watcher):
        """Test Google Drive with default interval using real argv."""
        mock_google_watcher_instance = MagicMock()
        mock_google_drive_watcher.return_value = mock_google_watcher_instance

        main()

        # Should use default 60 second interval
        mock_google_watcher_instance.watch_for_changes.assert_called_once_with(60)

    @patch("sys.argv", ["pipeline.py", "--source", "local", "--interval", "0"])
    @patch("src.rag_pipeline.pipeline.LocalFileWatcher")
    def test_main_with_zero_interval(self, mock_local_file_watcher):
        """Test with zero interval (edge case)."""
        mock_local_watcher_instance = MagicMock()
        mock_local_file_watcher.return_value = mock_local_watcher_instance

        main()

        mock_local_watcher_instance.watch_for_changes.assert_called_once_with(0)

    @patch("sys.argv", ["pipeline.py", "--source", "local", "--interval", "-10"])
    @patch("src.rag_pipeline.pipeline.LocalFileWatcher")
    def test_main_with_negative_interval(self, mock_local_file_watcher):
        """Test with negative interval (edge case)."""
        mock_local_watcher_instance = MagicMock()
        mock_local_file_watcher.return_value = mock_local_watcher_instance

        main()

        mock_local_watcher_instance.watch_for_changes.assert_called_once_with(-10)

    @patch("sys.argv", ["pipeline.py", "--source", "local"])
    @patch("src.rag_pipeline.pipeline.LocalFileWatcher")
    def test_main_local_watcher_exception(self, mock_local_file_watcher):
        """Test handling exception during watcher creation."""
        mock_local_file_watcher.side_effect = Exception("Watcher initialization failed")

        with pytest.raises(Exception, match="Watcher initialization failed"):
            main()

    @patch("sys.argv", ["pipeline.py", "--source", "google_drive"])
    @patch("src.rag_pipeline.pipeline.GoogleDriveWatcher")
    def test_main_google_drive_watch_exception(self, mock_google_drive_watcher):
        """Test handling exception during watch_for_changes."""
        mock_google_watcher_instance = MagicMock()
        mock_google_watcher_instance.watch_for_changes.side_effect = Exception("Watch failed")
        mock_google_drive_watcher.return_value = mock_google_watcher_instance

        with pytest.raises(Exception, match="Watch failed"):
            main()

    @patch("sys.argv", ["pipeline.py", "--source", "local", "--interval", "999999"])
    @patch("src.rag_pipeline.pipeline.LocalFileWatcher")
    def test_main_with_very_large_interval(self, mock_local_file_watcher):
        """Test with very large interval value."""
        mock_local_watcher_instance = MagicMock()
        mock_local_file_watcher.return_value = mock_local_watcher_instance

        main()

        mock_local_watcher_instance.watch_for_changes.assert_called_once_with(999999)

    @patch("sys.argv", ["pipeline.py"])
    def test_main_missing_required_source(self):
        """Test that missing --source argument raises SystemExit."""
        with pytest.raises(SystemExit):
            main()

    @patch("sys.argv", ["pipeline.py", "--source", "invalid_source"])
    def test_main_invalid_source(self):
        """Test that invalid source argument raises SystemExit."""
        with pytest.raises(SystemExit):
            main()

    @patch("sys.argv", ["pipeline.py", "--source", "local", "--interval", "not_a_number"])
    def test_main_invalid_interval_type(self):
        """Test that non-integer interval raises SystemExit."""
        with pytest.raises(SystemExit):
            main()
