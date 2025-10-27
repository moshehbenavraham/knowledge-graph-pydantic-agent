# GraphRAG Dashboard Bug Investigation Plan

## Goal
Investigate why existing dashboard widgets are NOT working - find and fix bugs ONLY. NO new features.

## Reported Issues

### Issue 1: Search Analytics - No Time Period Label
**Problem**: Metrics show numbers but don't indicate what time period they cover (default is 7d)
**Expected**: Should show "Last 7 days" or similar label
**Investigation**:
- Check streamlit_app.py:676-706 - search analytics rendering
- Verify window parameter is passed to get_search_metrics() (currently hardcoded "7d")
- Add label showing the time window being displayed

### Issue 2: Trends Over Time - Single Data Point Only
**Problem**: Shows "Data range: 2025-10-26 to 2025-10-26 (1 data point)" even when 7d window selected
**Expected**: Should show 7 days of data points for 7d window
**Investigation**:
- Query database directly: SELECT DATE(created_at), COUNT(*) FROM search_analytics WHERE created_at >= NOW() - INTERVAL '7 days' GROUP BY DATE(created_at) ORDER BY DATE(created_at);
- Check if only 1 day of data actually exists in search_analytics table
- Verify materialized view daily_search_summary is populated
- Check dashboard_handler.py:517-616 - get_time_series_data() logic
- Test if materialized view fallback query works (line 573-586)
- Verify date grouping for 7d/30d windows

### Issue 3: Intent Analysis - Shows Nothing
**Problem**: Pie chart section is completely empty
**Expected**: Should show distribution of detected intents from search_analytics
**Investigation**:
- Query database: SELECT detected_intent, COUNT(*) FROM search_analytics GROUP BY detected_intent;
- Check if get_intent_distribution() returns empty dict or error (line 184-243)
- Verify materialized view intent_distribution_7d has data
- Check if UI properly handles empty data (line 778-797)
- Look for exceptions in logs during intent rendering

### Issue 4: Tool Usage Analytics - Shows Nothing
**Problem**: Shows "No tool usage data available yet" message
**Expected**: Should show tool usage if tools are being used, or explain why it's empty
**Investigation**:
- Query database: SELECT COUNT(*) FROM tool_usage_analytics;
- Verify if tool_usage_analytics table is actually empty (likely true - tools not logged)
- Check if error is swallowed in get_tool_usage_metrics() (line 618-709)
- If table is empty, this is EXPECTED BEHAVIOR (no tool logging exists in code)
- Verify "no data" message displays correctly

### Issue 5: Agent Interactions - Shows Nothing
**Problem**: Shows "No agent interaction data available yet" message
**Expected**: Should show interactions if agent is used, or explain why it's empty
**Investigation**:
- Query database: SELECT COUNT(*) FROM agent_interactions;
- Verify if agent_interactions table is actually empty (likely true - interactions not logged)
- Check if error is swallowed in get_agent_interaction_metrics() (line 711-769)
- If table is empty, this is EXPECTED BEHAVIOR (no interaction logging exists in code)
- Verify "no data" message displays correctly

## Root Cause Hypothesis

**High Probability Issues**:
1. Only 1 day of actual search data exists -> Time series shows 1 point (DATA ISSUE, not code bug)
2. Intent analysis query broken or data missing -> Empty pie chart (BUG)
3. Tool/agent logging never implemented -> Tables empty (NOT A BUG, expected until logging added)
4. Time period label missing -> Easy UI fix (BUG)

**Low Probability Issues**:
1. Materialized views not refreshed -> Try clicking "Sync Views" button
2. Date grouping logic broken -> Test with manual SQL queries
3. Error handling hiding real errors -> Check logs

## Investigation Steps (Execute in Order)

### Step 1: Database Data Verification (30 min)
Check what data actually exists:
```sql
-- How much search data exists?
SELECT
    MIN(created_at) as first_search,
    MAX(created_at) as last_search,
    DATE(created_at) as date,
    COUNT(*) as searches_per_day
FROM search_analytics
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Intent distribution
SELECT detected_intent, strategy_used, COUNT(*)
FROM search_analytics
GROUP BY detected_intent, strategy_used;

-- Tool and agent tables
SELECT COUNT(*) FROM tool_usage_analytics;
SELECT COUNT(*) FROM agent_interactions;

-- Materialized views
SELECT * FROM daily_search_summary ORDER BY date DESC LIMIT 10;
SELECT * FROM intent_distribution_7d;
SELECT * FROM tool_performance_7d;
```

### Step 2: Code Review (30 min)
- Review get_time_series_data() date filtering logic
- Review get_intent_distribution() query construction
- Check error handling in all dashboard methods
- Verify materialized view refresh logic

### Step 3: Test Dashboard Queries Directly (30 min)
Run the exact queries from dashboard_handler.py in PostgreSQL to see results:
- get_search_metrics() query (line 97-112)
- get_time_series_data() query for 7d (line 544-557)
- get_intent_distribution() query (line 203-213)

### Step 4: UI Rendering Logic (20 min)
- Check if empty data causes UI to not render vs showing message
- Verify error states are caught and displayed
- Test with st.write() debug output for returned data

## Fixes to Implement (After Investigation)

### Fix 1: Add Time Period Label (5 min)
Location: streamlit_app.py:676-691
Add caption showing time window:
```python
st.header("Search Analytics")
st.caption(f"Showing metrics for the last {window_map[selected_window]}")
```

### Fix 2: Fix Intent Analysis (if broken query found)
Location: dashboard_handler.py:184-243
Depends on investigation findings

### Fix 3: Fix Time Series (if broken query found)
Location: dashboard_handler.py:517-616
Depends on investigation findings

### Fix 4: Improve Empty State Messages
Make it clearer why sections are empty:
- Tool usage: "No data - tool execution logging not yet implemented"
- Agent interactions: "No data - interaction logging not yet implemented"

## Testing Checklist
- Search analytics shows correct time period
- Time series displays all available data points
- Intent analysis shows data when search_analytics has records
- Tool/agent sections show appropriate "no data" messages
- All sections handle errors gracefully
- Materialized view refresh button works

## Files to Investigate/Modify
1. src/ui/streamlit_app.py (lines 676-1115) - Dashboard rendering
2. src/ui/features/dashboard_handler.py - All query methods
3. Database: search_analytics, tool_usage_analytics, agent_interactions tables
4. Materialized views: daily_search_summary, intent_distribution_7d, tool_performance_7d

## Expected Outcomes
- Search analytics shows "Last 7 days" label
- Time series shows all available data (may still be 1 point if only 1 day exists)
- Intent analysis displays pie chart when data exists
- Tool/agent sections clearly explain why empty
- All errors logged and displayed to user
- No crashes or silent failures
