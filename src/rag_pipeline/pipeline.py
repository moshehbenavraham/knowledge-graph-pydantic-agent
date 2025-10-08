import argparse

from sources.google_drive import GoogleDriveWatcher
from sources.local_files import LocalFileWatcher


def main():
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

    if args.source == "local":
        watcher = LocalFileWatcher()
        watcher.watch_for_changes(args.interval)
    elif args.source == "google_drive":
        watcher = GoogleDriveWatcher()
        watcher.watch_for_changes(args.interval)


if __name__ == "__main__":
    main()
