#!/bin/sh
# Skript: run_photo_workflow.sh
# Zweck: Startet den Photo-Workflow als Pipeline (Phase 1 + Phase 2).
# Autor: MaiTaiMa
# Erstellt: 2026-07-29
# Version: 1.1
# Requires: bash, docker, Python 3.11
# Usage: ./run_photo_workflow.sh [config_path]
#
# Änderungsprotokoll:
#   2026-07-29 | 1.0 | Initiale Version
#   2026-08-28 | 1.1 | Doppelte Aufrufe entfernt, nur noch pipeline
#
set -eu

CONFIG_PATH="${1:-/app/config/config.yaml}"

# Pipeline führt Phase 1 und Phase 2 in der konfigurierten Reihenfolge aus.
# Keine separaten Aufrufe von phase1/phase2, um doppelte Verarbeitung zu vermeiden.
python /app/app/photo_workflow.py --config "$CONFIG_PATH" pipeline
