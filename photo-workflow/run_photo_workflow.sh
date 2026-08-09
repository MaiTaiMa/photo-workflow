#!/bin/sh
set -eu
CONFIG_PATH="${1:-/app/config/config.yaml}"
python /app/app/photo_workflow.py --config "$CONFIG_PATH" phase1
python /app/app/photo_workflow.py --config "$CONFIG_PATH" phase2
python /app/app/photo_workflow.py --config "$CONFIG_PATH" pipeline