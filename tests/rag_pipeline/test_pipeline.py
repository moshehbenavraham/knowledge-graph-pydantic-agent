import pytest
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock, call

# Add src directory to path to import the module
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))
from rag_pipeline.pipeline import main
from rag_pipeline.sources.local_files import LocalFileWatcher
from rag_pipeline.sources.google_drive import GoogleDriveWatcher


class TestPipeline:
    @patch('rag_pipeline.pipeline.argparse.ArgumentParser')
    @patch('rag_pipeline.pipeline.LocalFileWatcher')
    @patch('rag_pipeline.pipeline.GoogleDriveWatcher')
    def test_main_local_source(self, MockGoogleDriveWatcher, MockLocalFileWatcher, MockArgumentParser):
        # Configure ArgumentParser mock
        mock_args = MagicMock()
        mock_args.source = "local"
        mock_args.interval = 30
        MockArgumentParser.return_value.parse_args.return_value = mock_args

        # Configure LocalFileWatcher mock
        mock_local_watcher_instance = MagicMock()
        MockLocalFileWatcher.return_value = mock_local_watcher_instance

        main()

        MockArgumentParser.assert_called_once()
        MockLocalFileWatcher.assert_called_once()
        mock_local_watcher_instance.watch_for_changes.assert_called_once_with(30)
        MockGoogleDriveWatcher.assert_not_called()

    @patch('rag_pipeline.pipeline.argparse.ArgumentParser')
    @patch('rag_pipeline.pipeline.LocalFileWatcher')
    @patch('rag_pipeline.pipeline.GoogleDriveWatcher')
    def test_main_google_drive_source(self, MockGoogleDriveWatcher, MockLocalFileWatcher, MockArgumentParser):
        # Configure ArgumentParser mock
        mock_args = MagicMock()
        mock_args.source = "google_drive"
        mock_args.interval = 90
        MockArgumentParser.return_value.parse_args.return_value = mock_args

        # Configure GoogleDriveWatcher mock
        mock_google_watcher_instance = MagicMock()
        MockGoogleDriveWatcher.return_value = mock_google_watcher_instance

        main()

        MockArgumentParser.assert_called_once()
        MockGoogleDriveWatcher.assert_called_once()
        mock_google_watcher_instance.watch_for_changes.assert_called_once_with(90)
        MockLocalFileWatcher.assert_not_called()

    @patch('rag_pipeline.pipeline.argparse.ArgumentParser')
    @patch('rag_pipeline.pipeline.LocalFileWatcher')
    @patch('rag_pipeline.pipeline.GoogleDriveWatcher')
    def test_main_default_interval(self, MockGoogleDriveWatcher, MockLocalFileWatcher, MockArgumentParser):
        # Configure ArgumentParser mock with default interval
        mock_args = MagicMock()
        mock_args.source = "local"
        mock_args.interval = 60 # Default value
        MockArgumentParser.return_value.parse_args.return_value = mock_args

        mock_local_watcher_instance = MagicMock()
        MockLocalFileWatcher.return_value = mock_local_watcher_instance

        main()

        mock_local_watcher_instance.watch_for_changes.assert_called_once_with(60)
