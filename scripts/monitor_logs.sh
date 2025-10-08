#!/bin/bash
# Real-time log monitoring script for AI with Apex Advanced RAG Agent
# Shows all DEBUG, INFO, WARNING, and ERROR logs as they happen

echo "=========================================="
echo "AI with Apex - Real-time Log Monitor"
echo "=========================================="
echo "Monitoring: /tmp/streamlit_debug.log"
echo "Press Ctrl+C to stop"
echo "=========================================="
echo ""

# Follow the log file in real-time
tail -f /tmp/streamlit_debug.log | while read line; do
    # Color code log levels
    if [[ $line == *"DEBUG"* ]]; then
        echo -e "\033[0;36m$line\033[0m"  # Cyan for DEBUG
    elif [[ $line == *"INFO"* ]]; then
        echo -e "\033[0;32m$line\033[0m"  # Green for INFO
    elif [[ $line == *"WARNING"* ]] || [[ $line == *"WARN"* ]]; then
        echo -e "\033[0;33m$line\033[0m"  # Yellow for WARNING
    elif [[ $line == *"ERROR"* ]]; then
        echo -e "\033[0;31m$line\033[0m"  # Red for ERROR
    else
        echo "$line"
    fi
done
