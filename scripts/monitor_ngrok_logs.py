#!/usr/bin/env python3
"""
Monitor ngrok HTTP request logs and write them to a file.

This script polls the ngrok API for HTTP requests and writes them to a log file
in a human-readable format.
"""

import json
import time
from datetime import datetime
from pathlib import Path

try:
    import httpx
except ImportError:
    print("httpx not found, trying urllib...")
    import urllib.error
    import urllib.request

    httpx = None


def format_request_log(req: dict) -> str:
    """Format ngrok request data into readable log entry."""
    timestamp = req.get("start", "")
    method = req["request"].get("method", "")
    uri = req["request"].get("uri", "")
    status = req["response"].get("status_code", 0)
    duration_ms = req.get("duration", 0) / 1000  # Convert microseconds to ms
    remote_addr = req.get("remote_addr", "")

    return (
        f"{timestamp} | {method:6s} {uri:60s} | "
        f"Status: {status} | {duration_ms:8.2f}ms | From: {remote_addr}"
    )


def monitor_ngrok_logs(log_file: Path, interval_seconds: int = 5):
    """
    Monitor ngrok API and write HTTP request logs to file.

    Args:
        log_file: Path to write logs
        interval_seconds: Polling interval
    """
    seen_ids = set()
    log_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"Starting ngrok log monitor - writing to {log_file}")
    print(f"Polling ngrok API every {interval_seconds} seconds...")

    with open(log_file, "a") as f:
        f.write(f"\n{'=' * 100}\n")
        f.write(f"Ngrok Log Monitor Started: {datetime.now().isoformat()}\n")
        f.write(f"{'=' * 100}\n\n")

        while True:
            try:
                # Use httpx if available, otherwise fall back to urllib
                if httpx:
                    response = httpx.get("http://localhost:4040/api/requests/http", timeout=2.0)
                    if response.status_code == 200:
                        data = response.json()
                        requests = data.get("requests", [])
                    else:
                        requests = []
                else:
                    req = urllib.request.Request("http://localhost:4040/api/requests/http")
                    with urllib.request.urlopen(req, timeout=2.0) as response:
                        data = json.loads(response.read().decode())
                        requests = data.get("requests", [])

                # Process new requests only
                new_requests = [r for r in requests if r["id"] not in seen_ids]

                for req in reversed(new_requests):  # Oldest first
                    log_entry = format_request_log(req)
                    f.write(log_entry + "\n")
                    f.flush()
                    print(log_entry)
                    seen_ids.add(req["id"])

                # Limit seen_ids size to prevent memory growth
                if len(seen_ids) > 1000:
                    # Keep only the most recent 500
                    recent_ids = {r["id"] for r in requests[:500]}
                    seen_ids.intersection_update(recent_ids)

            except Exception as e:
                # Handle connection errors (works for both httpx and urllib)
                error_type = type(e).__name__
                if (
                    "URLError" in error_type
                    or "RequestError" in error_type
                    or "ConnectError" in error_type
                ):
                    error_msg = f"[{datetime.now().isoformat()}] Waiting for ngrok to start (connection refused)"
                    print(error_msg)
                    f.write(error_msg + "\n")
                    f.flush()
                else:
                    # Other unexpected errors
                    error_msg = f"[{datetime.now().isoformat()}] Unexpected error: {e}"
                    print(error_msg)
                    f.write(error_msg + "\n")
                    f.flush()

            # Always sleep between polling attempts (even on error)
            time.sleep(interval_seconds)


if __name__ == "__main__":
    import sys

    log_dir = Path(__file__).parent.parent / "logs" / "ngrok_auth_logs"
    log_file = log_dir / f"ngrok_http_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    try:
        monitor_ngrok_logs(log_file)
    except KeyboardInterrupt:
        print("\nStopping ngrok log monitor...")
        sys.exit(0)
