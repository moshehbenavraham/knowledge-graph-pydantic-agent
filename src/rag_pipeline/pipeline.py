import argparse

import structlog
from sources.google_drive import GoogleDriveWatcher
from sources.local_files import LocalFileWatcher

structlog_logger = structlog.get_logger(__name__)


def main():
    structlog_logger.info("=" * 80)
    structlog_logger.info("RAG Pipeline main() called")

    parser = argparse.ArgumentParser(description="RAG Pipeline")
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        choices=["local", "google_drive"],
        help="The data source to watch.",
    )
    parser.add_argument(
        "--interval", type=int, default=60, help="The interval in seconds between checks."
    )
    args = parser.parse_args()

    structlog_logger.info(
        "Parsed command line arguments", source=args.source, interval=args.interval
    )

    if args.source == "local":
        structlog_logger.info("Initializing LocalFileWatcher...")
        watcher = LocalFileWatcher()
        structlog_logger.info("Starting local file watcher", interval_seconds=args.interval)
        watcher.watch_for_changes(args.interval)
        structlog_logger.info("LocalFileWatcher watch completed")
    elif args.source == "google_drive":
        structlog_logger.info("Initializing GoogleDriveWatcher...")
        watcher = GoogleDriveWatcher()
        structlog_logger.info("Starting Google Drive watcher", interval_seconds=args.interval)
        watcher.watch_for_changes(args.interval)
        structlog_logger.info("GoogleDriveWatcher watch completed")

    structlog_logger.info("main() completed successfully")


if __name__ == "__main__":
    main()
