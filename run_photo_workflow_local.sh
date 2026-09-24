#!/bin/bash
# Startet die photo-workflow Pipeline lokal im Podman-Container.
# Nutzt das Image localhost/photo-workflow:local (Smoke-Test 2026-09-24 bestanden).
set -e

PROJECT_DIR="$HOME/Programme/photo-workflow/photo-workflow"
cd "$PROJECT_DIR"

echo "=== photo-workflow (lokal) ==="
echo "Projektordner: $PROJECT_DIR"
echo "Image:         localhost/photo-workflow:local"
echo

podman run --rm -it \
  -v "$PROJECT_DIR/config:/app/config:ro" \
  -v "$PROJECT_DIR/../NAS_EXAMPLE:/app/NAS_EXAMPLE" \
  localhost/photo-workflow:local \
  --config /app/config/config.yaml pipeline

echo
echo "--- Lauf beendet ---"
read -n 1 -s -r -p "Beliebige Taste zum Schliessen druecken..."
