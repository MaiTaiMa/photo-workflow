#!/bin/bash
set -uo pipefail

PROJECT_DIR="/volume2/docker/photo-workflow"
LOG_DIR="/volume1/TEMP/WORKFLOW_DATA/runtime/logs"
LOG_FILE="${LOG_DIR}/task_scheduler_$(date +%Y-%m-%d_%H-%M-%S).log"

mkdir -p "$LOG_DIR"

echo "=== Start: $(date -Iseconds) ==="
cd "$PROJECT_DIR"

docker compose up --remove-orphans 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}

echo "=== Ende: $(date -Iseconds) | Exit-Code: ${EXIT_CODE} ==="
exit "${EXIT_CODE}"
