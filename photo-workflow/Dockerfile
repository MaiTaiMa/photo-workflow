# =============================================================================
# PROJECT:     photo-workflow
# FILE:        Dockerfile
# PURPOSE:     CPU-Runtime-Image fuer den Photo-Workflow (Synology amd64).
# CHANGES:
#   2026-09-09 | P7a | requirements-Pfad korrigiert, Systempakete ergaenzt.
#   2026-09-09 | P7b | Schlankes requirements-container.txt, keine Build-Tools.
#   2026-09-09 | P7c | ENV PYTHONPATH=/app (Skriptstart bricht Paketimport).
#   2026-09-09 | P7c | ENV PYTHONPATH=/app (Skriptstart bricht Paketimport).
# =============================================================================
FROM python:3.11-slim

# Laufzeit-Systempakete: OpenCV (libglib2.0) und ExifTool-CLI fuer XMP/EXIF.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 libimage-exiftool-perl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONPATH=/app
COPY requirements-container.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY app /app/app
COPY config /app/config
ENTRYPOINT ["python", "/app/app/photo_workflow.py"]
