#!/bin/bash
# Service stopper for devkit-plugin
# Stops all services started by serv-start.sh
#
# Usage: serv-stop.sh <project_dir>

set -e

PROJECT_DIR="${1:-.}"

cd "$PROJECT_DIR"

PIDS_FILE=".serv/pids"

if [ ! -f "$PIDS_FILE" ]; then
    echo "⚠️ No services running (.serv/pids not found)"
    exit 0
fi

echo "🛑 Stopping services..."
echo ""

stopped=0
failed=0

while IFS=: read -r name pid; do
    if [ -n "$pid" ]; then
        if kill -0 "$pid" 2>/dev/null; then
            # Process exists, kill it and its children
            pkill -P "$pid" 2>/dev/null || true
            kill "$pid" 2>/dev/null || true
            echo "✓ Stopped $name (PID $pid)"
            ((stopped++))
        else
            echo "⚠️ $name (PID $pid) already stopped"
        fi
    fi
done < "$PIDS_FILE"

# Clean up
rm -f "$PIDS_FILE"

echo ""
echo "---"
echo "Stopped $stopped service(s)"
echo ""
echo "Logs preserved in .serv/*.log"
echo "Clean logs: rm -rf .serv/"
