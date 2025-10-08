# Manual Test Scripts

This directory contains standalone test scripts for manual testing and debugging.

## Files

- `test_db_connection.py` - Test PostgreSQL/Supabase database connectivity
- `test_supabase_rest.py` - Test Supabase REST API fallback
- `test_web_search.py` - Test web search functionality (Jina API)

## Usage

Run any test directly from the project root:

```bash
python tests/manual/test_db_connection.py
python tests/manual/test_supabase_rest.py
python tests/manual/test_web_search.py
```

These scripts are for manual testing and debugging purposes. For automated tests, see the main `tests/` directory.
