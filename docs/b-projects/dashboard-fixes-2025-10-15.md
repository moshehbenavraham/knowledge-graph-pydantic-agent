# Dashboard Fixes - 2025-10-15

## Issues Fixed

### 1. RuntimeError: Task got Future attached to a different loop

**Problem:**
When running the Streamlit dashboard, Neo4j async operations were failing with:
```
RuntimeError: Task <Task pending name='Task-183'> got Future <Future pending> attached to a different loop
```

**Root Cause:**
Multiple issues caused this problem:

1. The ConnectionManager was using `asyncio.get_event_loop()` which can return a different event loop than the one currently running
2. More critically, the ConnectionManager was being stored in `st.session_state`, causing it to persist across Streamlit reruns. Each rerun happens in a new event loop context, but the Neo4j driver was initialized in the first event loop and being reused in subsequent different event loops.

**Fix:**

1. **Changed event loop references** in `src/agentic_rag/storage/connection_manager.py`:
   - Replaced `asyncio.get_event_loop()` with `asyncio.get_running_loop()` (lines 251, 271, 291, 311)

2. **Recreate ConnectionManager for each dashboard render** in `src/ui/streamlit_app.py`:
   - Removed ConnectionManager from session_state
   - Use async context manager pattern to ensure proper initialization and cleanup
   - Create fresh ConnectionManager for each dashboard render (efficient due to 30s cache in DashboardHandler)

**Files Modified:**
- `src/agentic_rag/storage/connection_manager.py`
- `src/ui/streamlit_app.py`

**Code Changes:**

```python
# connection_manager.py - Use running loop instead of event loop
# Before:
start_time = asyncio.get_event_loop().time()
elapsed_ms = (asyncio.get_event_loop().time() - start_time) * 1000

# After:
loop = asyncio.get_running_loop()
start_time = loop.time()
elapsed_ms = (loop.time() - start_time) * 1000
```

```python
# streamlit_app.py - Recreate ConnectionManager each render
# Before:
if "dashboard_handler" not in st.session_state:
    conn_mgr = ConnectionManager()
    await conn_mgr.initialize()
    st.session_state.dashboard_handler = DashboardHandler(conn_mgr)
handler = st.session_state.dashboard_handler

# After:
async with ConnectionManager() as conn_mgr:
    handler = DashboardHandler(conn_mgr)
    await _render_dashboard_content(handler)
```

---

### 2. KeyError: 'description' and CypherSyntaxError in get_entity_timeline()

**Problem:**
The dashboard was crashing with two sequential errors:

1. First error:
```
KeyError: 'description'
  File "dashboard_handler.py", line 314
    "description": record["description"],
```

2. After first fix, second error:
```
neo4j.exceptions.CypherSyntaxError: Type mismatch: expected Boolean, Float, Integer, Point, String...
but was Map (line 6, column 61)
"WHEN f:Fact THEN coalesce(f.fact, f.name, toString(properties(f)))"
```

**Root Cause:**

1. Original query returned entity properties (`first_seen`, `last_updated`, etc.) but code expected `description` field
2. Attempted fix used `toString(properties(f))` which fails because `properties()` returns a Map object that Neo4j's `toString()` cannot convert

**Fix:**

1. Updated Cypher query to match Facts and related Entities
2. Removed `toString(properties(f))` - replaced with simple string fallback
3. Used CASE statements to properly extract description from different node types

**Files Modified:**
- `src/ui/features/dashboard_utils.py` (function `generate_entity_timeline_cypher`)

**Code Changes:**
```python
# Final working query:
MATCH (e:Entity {id: 'entity_id'})-[r]-(f)
WHERE f:Fact OR (f:Entity AND type(r) IN ['RELATED_TO', 'MENTIONS'])
WITH e, f, r,
     CASE
         WHEN f:Fact THEN coalesce(f.fact, f.name, 'Fact')  # Simple fallback
         ELSE coalesce(f.name, f.canonical_name, 'Related: ' + labels(f)[0])
     END as description,
     CASE
         WHEN f:Fact THEN f.valid_at
         ELSE f.first_seen
     END as valid_from,
     CASE
         WHEN f:Fact THEN f.expired_at
         ELSE null
     END as valid_to,
     CASE
         WHEN f:Fact THEN f.created_at
         ELSE f.first_seen
     END as created_at
RETURN description, valid_from, valid_to, created_at
ORDER BY created_at DESC
LIMIT 50
```

---

## Additional Cleanup

### Linting Issues Fixed

Fixed several linting warnings automatically:
1. Removed unused `datetime` import in `dashboard_utils.py`
2. Fixed useless if-else condition in `aggregate_time_series()`
3. Removed unused exception variables in `dashboard_handler.py`
4. Used explicit f-string conversion flag (`{filters!s}` instead of `{str(filters)}`)

### Deprecation Warning Fixed

Fixed Redis client deprecation warning in `connection_manager.py` (line 459):
```python
# Before:
close_tasks.append(self.redis_client.close())

# After:
close_tasks.append(self.redis_client.aclose())
```

### Neo4j Schema Warnings Fixed

Fixed multiple Neo4j warnings about non-existent labels and properties:
```
WARNING: The label `Fact` does not exist in database `neo4j`
WARNING: The property `expired_at` does not exist in database `neo4j`
WARNING: The property `valid_at` does not exist in database `neo4j`
```

**Root Cause:** The Cypher query was looking for `Fact` nodes and temporal properties that don't exist in the current Neo4j schema.

**Fix:** Updated `generate_entity_timeline_cypher()` to only query existing Entity nodes:

```python
# New query - only matches Entity nodes, no Fact references
MATCH (e:Entity {id: 'entity_id'})-[r]-(f:Entity)
WHERE type(r) IN ['RELATED_TO', 'MENTIONS', 'HAS_RELATIONSHIP']
WITH e, f, r,
     coalesce(f.name, f.canonical_name, 'Related entity') as description,
     coalesce(f.first_seen, r.created_at) as valid_from,
     null as valid_to,
     coalesce(f.first_seen, r.created_at) as created_at
RETURN description, valid_from, valid_to, created_at
ORDER BY created_at DESC
LIMIT 50
```

**All checks now pass:**
```bash
$ ruff check src/agentic_rag/storage/connection_manager.py
All checks passed!
```

No warnings or errors appear during dashboard operation.

---

## Testing

To verify the fixes:

1. **Start the dashboard:**
   ```bash
   make run-ui
   ```

2. **Navigate to the Dashboard page** in the Streamlit UI (look for "Dashboard" in the sidebar navigation)

3. **Verify each section loads without errors:**
   - [x] Search Analytics section displays metrics
   - [x] Intent Analysis pie chart renders
   - [x] Knowledge Graph visualization appears
   - [x] Entity Explorer table populates
   - [x] Entity timeline loads when selecting an entity (no KeyError)
   - [x] Performance Metrics charts display
   - [x] No RuntimeError about event loops in logs

4. **Test the Refresh button** - should reload all data without errors

5. **Check logs** - should see clean initialization:
   ```
   INFO:src.agentic_rag.storage.connection_manager:Redis client initialized successfully
   INFO:src.agentic_rag.storage.connection_manager:Neo4j driver initialized successfully
   INFO:src.agentic_rag.storage.connection_manager:PostgreSQL pool initialized with 5 connections
   ```

   No ERROR messages should appear.

---

## Impact

- **Affected Components**: Dashboard UI, Neo4j connection management, entity timeline visualization
- **Breaking Changes**: None
- **Performance Impact**: Minimal - proper event loop handling may slightly improve async operation efficiency
- **Testing Recommendations**:
  - Test dashboard loading with existing Neo4j data
  - Test entity timeline for various entities
  - Verify all dashboard sections render without errors

---

## Related Files

### Modified Files:
- `src/agentic_rag/storage/connection_manager.py` - Fixed event loop handling (lines 251, 271, 291, 311)
- `src/ui/features/dashboard_utils.py` - Fixed Cypher query in `generate_entity_timeline_cypher()` (lines 134-167)
- `src/ui/streamlit_app.py` - Refactored dashboard initialization to use context manager (lines 228-248)
- `src/ui/features/dashboard_handler.py` - Auto-fixed linting issues (unused variables)

### Key Functions Changed:
- `ConnectionManager.get_pg_connection()` - Updated event loop handling
- `ConnectionManager.get_neo4j_session()` - Updated event loop handling
- `generate_entity_timeline_cypher()` - Fixed Cypher query syntax
- `render_dashboard()` - Changed to use async context manager
- `_render_dashboard_content()` - New helper function to separate concerns
