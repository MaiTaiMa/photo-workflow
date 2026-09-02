# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/phase3_transfer.py
# PURPOSE:     Photo Workflow Module
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path

from .path_security import ensure_within, validate_publish_target


class TransferError(ValueError):
    """Raised when PHASE3 transfer verification fails."""


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _files(root: Path) -> list[dict]:
    result = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            result.append({"relative_path": str(path.relative_to(root)),
                           "size": path.stat().st_size, "hash": _hash(path)})
    return result


def _check_tool(tool_path: str) -> tuple[bool, str]:
    resolved = Path(tool_path)
    if not resolved.exists():
        return False, f"tool_not_found:{tool_path}"
    if not os.access(resolved, os.X_OK):
        return False, f"tool_not_executable:{tool_path}"
    return True, "ok"


def trigger_indexing(target_path: Path, cfg_indexing: dict) -> dict:
    """
    Loest Synology-Photos-Indexierung via synofoto-bin-index-tool aus.
    Nur im NAS-Docker-Deployment verfuegbar.
    """
    tool_path = str(cfg_indexing.get(
        "tool_path",
        "/usr/local/bin/synofoto-bin-index-tool",
    ))
    index_type = str(cfg_indexing.get("index_type", "basic"))
    timeout = int(cfg_indexing.get("timeout_seconds", 120))

    valid_types = {"basic", "basic_reindex", "reindex"}
    if index_type not in valid_types:
        return {"status": "config_error", "reason": f"invalid index_type:{index_type}"}

    ok, reason = _check_tool(tool_path)
    if not ok:
        return {
            "status": "tool_unavailable",
            "reason": reason,
            "hint": (
                "Nur auf Synology NAS mit korrekt gemountem Binary verfuegbar. "
                "Siehe docker-compose.yml und config.yaml finalization.publish_to_synology_photos."
            ),
        }

    import subprocess
    cmd = [tool_path, "-t", index_type, "-i", str(target_path)]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False,
        )
        if result.returncode == 0:
            return {"status": "indexed", "index_type": index_type, "target": str(target_path)}
        return {
            "status": "index_failed",
            "returncode": result.returncode,
            "stderr": (result.stderr or "").strip()[:200],
        }
    except subprocess.TimeoutExpired:
        return {"status": "index_timeout", "reason": f"timeout after {timeout}s"}
    except OSError as exc:
        return {"status": "index_os_error", "reason": str(exc)}


def _write_manifest_atomically(manifest_path: Path, manifest: dict) -> None:
    """
    Schreibt das Finalisierungsmanifest atomar in das Zielverzeichnis.

    Ablauf: temporaere Datei im selben Verzeichnis -> fsync -> os.replace.
    Dadurch ist nach einem Abbruch entweder die alte oder die vollstaendige neue
    Manifest-Version sichtbar, niemals eine teilweise geschriebene JSON-Datei.
    """
    import json
    import os
    import tempfile

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{manifest_path.name}.",
        suffix=".tmp",
        dir=manifest_path.parent,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, manifest_path)
    except Exception:
        try:
            Path(temp_name).unlink(missing_ok=True)
        except Exception:
            pass
        raise


def transfer_batch(
    source: str | Path,
    target: str | Path,
    config: dict,
    *,
    batch_id: str,
    mode: str = "copy",
    dry_run: bool = False,
) -> dict:
    """
    Phase-3-Transfer: 04_TEMP_FINAL -> publish_root mit atomarem Manifest.
    """
    import json
    import shutil
    import subprocess
    import tempfile

    cfg_final = config.get("finalization", {})
    cfg_publish = cfg_final.get("publish_to_synology_photos", {})

    if not bool(cfg_final.get("enabled", False)):
        return {"status": "finalization_disabled", "batch_id": batch_id}

    if not bool(cfg_publish.get("enabled", False)):
        return {"status": "publish_disabled", "batch_id": batch_id}

    effective_mode = mode if mode != "copy" else str(cfg_publish.get("mode", "copy"))
    effective_dry_run = dry_run or bool(cfg_publish.get("dry_run", False))

    if effective_mode not in {"copy", "move"}:
        raise TransferError(f"Unsupported transfer mode: {effective_mode}")

    base = config["paths"].get("basedir") or config["paths"].get("base_dir")
    source_path = ensure_within(base, source, allow_missing=False)
    target_path = validate_publish_target(config, target)

    source_files = _files(source_path)
    manifest = {
        "batch_id": batch_id,
        "source_batch_path": str(source_path),
        "target_batch_path": str(target_path),
        "transfer_mode": effective_mode,
        "dry_run": effective_dry_run,
        "files": source_files,
        "indexing": None,
    }

    if effective_dry_run:
        manifest["status"] = "planned"
        return manifest

    target_path.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(
        prefix=f".{target_path.name}.",
        dir=target_path.parent,
    ))
    try:
        shutil.copytree(source_path, staging / source_path.name)
        staged = staging / source_path.name

        if _files(staged) != source_files:
            raise TransferError("Staging verification failed: file mismatch")
        if target_path.exists():
            raise TransferError(f"Target already exists: {target_path}")

        os.replace(staged, target_path)

        if effective_mode == "move":
            shutil.rmtree(source_path)

        manifest["status"] = "transferred"
        manifest["target_files"] = _files(target_path)

        # Manifest atomar schreiben
        manifest_path = target_path / "finalization_manifest.json"
        _write_manifest_atomically(manifest_path, manifest)

        # Indexing-Trigger
        cfg_indexing = cfg_publish.get("indexing", {})
        if bool(cfg_indexing.get("enabled", True)):
            manifest["indexing"] = trigger_indexing(target_path, cfg_indexing)
            # Manifest nach Indexing aktualisieren
            _write_manifest_atomically(manifest_path, manifest)
        else:
            manifest["indexing"] = {"status": "disabled"}
        # Album-Upsert (nur wenn enabled)
        cfg_album = cfg_publish.get("album_upsert", {})
        if bool(cfg_album.get("enabled", False)):
            from app.synology_photos_adapter import SynologyPhotosAdapter
            adapter = SynologyPhotosAdapter(cfg)
            if adapter.album_upsert and adapter.healthcheck().status == "ready":
                # TODO: Personen aus Batch ermitteln und Alben zuordnen
                # Dies erfordert Zugriff auf die erkannten Personen aus dem Batch
                # Implementierung nach Bedarf
                manifest["album_upsert"] = {"status": "ready", "adapter": "SynologyPhotosAdapter"}
            else:
                manifest["album_upsert"] = {"status": "disabled", "reason": "adapter_not_ready"}
        else:
            manifest["album_upsert"] = {"status": "disabled"}


    finally:
        shutil.rmtree(staging, ignore_errors=True)

    return manifest
