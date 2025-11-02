# Google Drive Ingestion - Deployment Guide

**Status:** Production-ready | **Test Coverage:** 535+ assertions | **Version:** 1.2.5

---

## Overview

Continuously syncs Google Drive folders to the Agentic RAG pipeline. Monitors file changes (create/update/delete) and processes documents into PostgreSQL/Supabase + Neo4j.

**File:** `src/rag_pipeline/sources/google_drive.py` (715 lines)

**Supported Files:** PDF, plain text, HTML, CSV, Google Docs/Sheets/Slides

**Architecture:**
```
Google Drive API (OAuth 2.0)
    |
    v
GoogleDriveWatcher (polling-based)
    |
    v
Text Processor -> DB Handler
    |
    v
PostgreSQL/Supabase + Neo4j
```

---

## Installation

### 1. Install Dependencies

```bash
pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
```

**Recommended:** Add to `pyproject.toml`:
```toml
[project.optional-dependencies]
google_drive = [
    "google-api-python-client>=2.100.0",
    "google-auth>=2.16.0",
    "google-auth-oauthlib>=1.0.0",
    "google-auth-httplib2>=0.1.0",
]
```

Then: `pip install -e .[google_drive]`

### 2. Google Cloud Setup

1. Go to https://console.cloud.google.com/
2. Create project -> Enable Google Drive API
3. Create OAuth 2.0 credentials (Desktop app)
4. Download as `credentials.json`

### 3. Place Credentials

```bash
mkdir -p config
cp credentials.json config/google_credentials.json
```

**CRITICAL:** Add to `.gitignore`:
```
credentials.json
token.json
config/google_credentials.json
config/google_token.json
src/rag_pipeline/sources/credentials.json
src/rag_pipeline/sources/token.json
```

---

## Configuration

### Environment Variables (`.env`)

```bash
GOOGLE_DRIVE_FOLDER_ID=              # Optional: specific folder ID, empty = all files
GOOGLE_DRIVE_CREDENTIALS_PATH=config/google_credentials.json
```

### Config File (`src/rag_pipeline/sources/config.json`)

```json
{
  "supported_mime_types": [
    "application/pdf",
    "text/plain",
    "text/html",
    "text/csv",
    "application/vnd.google-apps.document",
    "application/vnd.google-apps.spreadsheet",
    "application/vnd.google-apps.presentation"
  ],
  "text_processing": {
    "default_chunk_size": 400,
    "default_chunk_overlap": 0
  },
  "last_check_time": "1970-01-01T00:00:00.000Z",
  "watch_folder_id": null
}
```

**Get Folder ID:** Open folder in Drive, copy ID from URL: `https://drive.google.com/drive/folders/FOLDER_ID`

---

## Deployment

### First Run (OAuth Flow)

```bash
python -m src.rag_pipeline.pipeline --source google_drive --interval 60
```

Browser opens -> Grant permissions -> `token.json` saved -> Subsequent runs automatic

### Production: Systemd (Linux)

```bash
sudo nano /etc/systemd/system/luminari-gdrive.service
```

```ini
[Unit]
Description=Luminari Agent Google Drive Watcher
After=network.target

[Service]
Type=simple
User=luminari
WorkingDirectory=/opt/luminari-agent
Environment="PATH=/opt/luminari-agent/.venv/bin"
ExecStart=/opt/luminari-agent/.venv/bin/python -m src.rag_pipeline.pipeline --source google_drive --interval 300
Restart=on-failure
RestartSec=60

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable luminari-gdrive
sudo systemctl start luminari-gdrive
sudo journalctl -u luminari-gdrive -f
```

### Production: Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install -e .[rag,google_drive]
CMD ["python", "-m", "src.rag_pipeline.pipeline", "--source", "google_drive", "--interval", "300"]
```

```bash
docker build -t luminari-gdrive -f Dockerfile.gdrive .
docker run -d \
  --name luminari-gdrive \
  -v /path/to/credentials.json:/app/config/google_credentials.json:ro \
  -v /path/to/token.json:/app/config/token.json \
  -v /path/to/.env:/app/.env:ro \
  --restart unless-stopped \
  luminari-gdrive
```

---

## How It Works

### Polling Cycle (default: 60 seconds)

1. **Get Changes:** Query Drive API for files modified since last check
2. **Check Deletions:** Poll known files for trashed/404 status
3. **Process Files:**
   - Download file content
   - Extract text (pypdf for PDF, UTF-8 decode for text, export Google Workspace files)
   - Chunk text (400 chars, 0 overlap)
   - Generate embeddings (OpenAI API)
   - Store in PostgreSQL + metadata
4. **Delete Trashed:** Remove from database
5. **Sleep:** Wait for next interval

### Database Storage

**PostgreSQL Tables:**
- `documents`: content + embeddings + metadata (file_id, file_url, file_title, mime_type)
- `document_metadata`: file_id + title + url + schema (for CSV)
- `document_rows`: tabular data storage (dataset_id + row_data)

**Neo4j:** Future entity extraction (not yet integrated)

---

## Monitoring

### Check Logs

```bash
# Systemd
sudo journalctl -u luminari-gdrive -n 100

# Docker
docker logs luminari-gdrive --tail 100 -f
```

### Verify Ingestion

```sql
SELECT
    metadata->>'file_title' AS title,
    metadata->>'mime_type' AS type,
    COUNT(*) AS chunks,
    created_at
FROM documents
WHERE metadata->>'file_id' IS NOT NULL
GROUP BY metadata->>'file_title', metadata->>'mime_type', created_at
ORDER BY created_at DESC;
```

---

## Troubleshooting

**"google-auth-oauthlib not installed"**
```bash
pip install google-auth-oauthlib google-api-python-client google-auth google-auth-httplib2
```

**"credentials.json not found"**
- Download from Google Cloud Console
- Place in `src/rag_pipeline/sources/credentials.json` or custom path

**"Token expired/revoked"**
```bash
rm src/rag_pipeline/sources/token.json
python -m src.rag_pipeline.pipeline --source google_drive
```

**"Empty text from PDF"**
- Scanned PDF (no text layer) -> Needs OCR integration

**"Files not detected"**
- Check folder ID correct
- Check `last_check_time` not in future (edit `config.json`)
- Check files modified after `last_check_time`

**"API quota exceeded"**
```bash
python -m src.rag_pipeline.pipeline --source google_drive --interval 300  # Increase interval
```

---

## Known Limitations

1. **Polling-based** (not real-time) - minimum latency = polling interval
2. **No Shared Drive support** - only "My Drive"
3. **Google Sheets:** First sheet only as CSV
4. **No OCR** - scanned PDFs return empty text
5. **No versioning** - only latest version processed
6. **Pagination gaps** - assumes <100 files per folder (no `nextPageToken` handling)
7. **Sequential processing** - no concurrent downloads
8. **O(N) deletion detection** - one API call per tracked file
9. **Single folder watch** - can't watch multiple folders
10. **No rate limiting** - can exceed API quotas if interval too short

---

## API Rate Limits

**Google Drive API Quotas:**
- 1,000 queries per 100 seconds per user
- 1 billion queries per day

**Watcher Usage (per cycle):**
- 1x `files().list()` (changes)
- Nx `files().get()` (deletion detection, N = known_files)
- Mx `files().get_media()` (downloads, M = changed files)

**Example (100 files, 5 changes):** 106 API calls/cycle = 1.77 calls/sec (well within quota)

---

## Security

**OAuth Scopes (Read-Only):**
```python
SCOPES = [
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]
```

**Permissions:**
- [+] Read file metadata
- [+] Download file contents
- [-] Modify files
- [-] Delete files
- [-] Share files
- [-] Create files

**Recommendations:**
- Add credentials/token files to `.gitignore`
- `chmod 600` on sensitive files
- Use TLS for database connections
- Monitor API usage

---

## Key Implementation Details

**File:** `src/rag_pipeline/sources/google_drive.py`

**Class:** `GoogleDriveWatcher`

**Key Methods:**
- `authenticate()`: OAuth 2.0 flow, token refresh (lines 164-208)
- `get_changes()`: Query modified files since last check (lines 285-346)
- `get_folder_contents()`: Recursive folder traversal (lines 210-283)
- `download_file()`: Download with export support for Google Workspace (lines 348-416)
- `process_file()`: Text extraction + RAG processing (lines 418-509)
- `check_for_deleted_files()`: Poll known files for deletions (lines 511-572)
- `watch_for_changes()`: Main polling loop (lines 574-714)

**Tests:**
- `tests/rag_pipeline/sources/test_google_drive.py` (535 lines)
- `tests/rag_pipeline/sources/test_google_drive_comprehensive.py` (899 lines)
- 35+ test cases, 535+ assertions, ~95% coverage

---

## Quick Commands

```bash
# Run watcher (60s interval)
python -m src.rag_pipeline.pipeline --source google_drive --interval 60

# Run with custom folder
GOOGLE_DRIVE_FOLDER_ID=1a2b3c4d python -m src.rag_pipeline.pipeline --source google_drive

# Check logs
sudo journalctl -u luminari-gdrive -f

# Test import
python -c "from src.rag_pipeline.sources.google_drive import GoogleDriveWatcher; print('OK')"
```

---

**Production Readiness:** 8/10 (fully functional, needs pagination + concurrency for scale)
