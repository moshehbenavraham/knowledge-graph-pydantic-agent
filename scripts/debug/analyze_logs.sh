#!/bin/bash
#
# analyze_logs.sh - Parse and analyze application logs
#
# Usage: ./analyze_logs.sh [logfile] [--errors] [--warnings] [--search PATTERN]
#
# Analyzes:
#   - Error frequency and types
#   - Warning patterns
#   - Performance metrics (if profiling enabled)
#   - Circuit breaker events
#

set -euo pipefail

# Colors (GREEN used in success messages)
if [ -t 1 ]; then
    RED='\033[0;31m'
    # shellcheck disable=SC2034
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    RED=''
    # shellcheck disable=SC2034
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
fi

LOGFILE=""
SHOW_ERRORS=false
SHOW_WARNINGS=false
SEARCH_PATTERN=""
TAIL_MODE=false
TAIL_LINES=100

usage() {
    cat << EOF
Usage: $0 [logfile] [options]

Options:
  -e, --errors      Show error summary
  -w, --warnings    Show warning summary
  -s, --search PAT  Search for pattern
  -t, --tail N      Show last N lines (default: 100)
  -f, --follow      Follow log file (like tail -f)
  -h, --help        Show this help

Examples:
  $0 app.log --errors
  $0 app.log --search "circuit_breaker"
  $0 --tail 50

EOF
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--errors)
            SHOW_ERRORS=true
            shift
            ;;
        -w|--warnings)
            SHOW_WARNINGS=true
            shift
            ;;
        -s|--search)
            SEARCH_PATTERN="$2"
            shift 2
            ;;
        -t|--tail)
            TAIL_MODE=true
            TAIL_LINES="${2:-100}"
            shift 2
            ;;
        -f|--follow)
            TAIL_MODE=true
            TAIL_LINES="-f"
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            if [ -z "$LOGFILE" ] && [ -f "$1" ]; then
                LOGFILE="$1"
            fi
            shift
            ;;
    esac
done

# If no logfile specified, try to read from stdin or default location
if [ -z "$LOGFILE" ]; then
    if [ -t 0 ]; then
        # No stdin, check for default log locations
        if [ -f "logs/app.log" ]; then
            LOGFILE="logs/app.log"
        else
            echo "Usage: $0 <logfile> [options]"
            echo "Or pipe logs: make run-ui 2>&1 | $0 --errors"
            exit 1
        fi
    else
        # Reading from stdin
        LOGFILE="/dev/stdin"
    fi
fi

echo "=================================="
echo "Log Analysis - Agentic RAG"
echo "=================================="
echo ""

# Function to count patterns
count_pattern() {
    local pattern="$1"
    local label="$2"
    local count
    count=$(grep -c "$pattern" "$LOGFILE" 2>/dev/null || echo "0")
    echo "$label: $count"
}

# Summary section
echo -e "${BLUE}=== Log Summary ===${NC}"
if [ -f "$LOGFILE" ]; then
    TOTAL_LINES=$(wc -l < "$LOGFILE")
    echo "Total lines: $TOTAL_LINES"
    echo "File: $LOGFILE"
else
    echo "Reading from stdin..."
fi
echo ""

# Error analysis
if [ "$SHOW_ERRORS" = true ]; then
    echo -e "${RED}=== Error Analysis ===${NC}"

    echo ""
    echo "Error counts by type:"
    grep -i "error" "$LOGFILE" 2>/dev/null | \
        grep -oE '\[error\]|\berror\b|ERROR' | \
        sort | uniq -c | sort -rn | head -10 || echo "  No errors found"

    echo ""
    echo "Recent errors (last 5):"
    grep -i "error" "$LOGFILE" 2>/dev/null | tail -5 || echo "  No errors found"

    echo ""
fi

# Warning analysis
if [ "$SHOW_WARNINGS" = true ]; then
    echo -e "${YELLOW}=== Warning Analysis ===${NC}"

    echo ""
    echo "Warning counts:"
    WARN_COUNT=$(grep -ci "warning\|warn" "$LOGFILE" 2>/dev/null || echo "0")
    echo "  Total warnings: $WARN_COUNT"

    echo ""
    echo "Recent warnings (last 5):"
    grep -i "warning\|warn" "$LOGFILE" 2>/dev/null | tail -5 || echo "  No warnings found"

    echo ""
fi

# Pattern search
if [ -n "$SEARCH_PATTERN" ]; then
    echo -e "${BLUE}=== Search Results: '$SEARCH_PATTERN' ===${NC}"
    echo ""

    MATCH_COUNT=$(grep -c "$SEARCH_PATTERN" "$LOGFILE" 2>/dev/null || echo "0")
    echo "Matches found: $MATCH_COUNT"

    if [ "$MATCH_COUNT" -gt 0 ]; then
        echo ""
        echo "Sample matches:"
        grep "$SEARCH_PATTERN" "$LOGFILE" 2>/dev/null | head -10
    fi

    echo ""
fi

# Circuit breaker events
echo -e "${BLUE}=== Circuit Breaker Events ===${NC}"
count_pattern "circuit.*open" "  Circuit opened"
count_pattern "circuit.*closed" "  Circuit closed"
count_pattern "circuit.*half" "  Half-open tests"
echo ""

# Retry events
echo -e "${BLUE}=== Retry Events ===${NC}"
count_pattern "retry.*attempt" "  Retry attempts"
count_pattern "max.*retries" "  Max retries exceeded"
echo ""

# Performance metrics (if profiling enabled)
echo -e "${BLUE}=== Performance Metrics ===${NC}"
if grep -q "duration_ms" "$LOGFILE" 2>/dev/null; then
    echo "Slowest operations (by duration_ms):"
    grep "duration_ms" "$LOGFILE" 2>/dev/null | \
        grep -oE 'duration_ms=[0-9.]+' | \
        sed 's/duration_ms=//' | \
        sort -rn | \
        head -5 | \
        while read -r ms; do
            printf "  %.2f ms\n" "$ms"
        done
else
    echo "  No performance data found (set PROFILING_ENABLED=true)"
fi
echo ""

# Handler activity
echo -e "${BLUE}=== Handler Activity ===${NC}"
count_pattern "BaseHandler" "  BaseHandler"
count_pattern "StreamingHandler" "  StreamingHandler"
count_pattern "MemoryHandler" "  MemoryHandler"
count_pattern "MCPHandler" "  MCPHandler"
echo ""

# Tail mode
if [ "$TAIL_MODE" = true ]; then
    echo -e "${BLUE}=== Recent Log Entries ===${NC}"
    if [ "$TAIL_LINES" = "-f" ]; then
        tail -f "$LOGFILE"
    else
        tail -n "$TAIL_LINES" "$LOGFILE"
    fi
fi

echo "=================================="
echo "Analysis complete"
