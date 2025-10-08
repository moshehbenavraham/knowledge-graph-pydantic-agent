import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src directory to path to import the module
sys.path.append(str(Path(__file__).parent.parent.parent.resolve() / "src"))
from rag_pipeline.pipeline import main


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
