# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/faces/face_proposal_activation.py
# PURPOSE:     Photo Workflow Module
# AUTHOR:      Matzethias
# DATE:        2026-09-03
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
#   Erkennt manuell verschobene Dateien new_faces/ → reference/ und registriert sie in selection.json als aktivierte Referenzbilder.
# =============================================================================


from __future__ import annotations

from pathlib import Path

from .proposal_contract import load_proposal_contract, save_proposal_contract


def detect_activated_faces(pool_root: Path) -> list[dict[str, object]]:
    """Erkennt manuell verschobene Gesichts-Crops in reference/.

    Vergleicht die Einträge in selection.json mit dem tatsächlichen
    Dateisystem unter reference/ und markiert neue Referenzbilder als
    "activated" im Proposal-Contract.

    Args:
        pool_root: Pfad zum Personen-Verzeichnis (faces/<slug>).

    Returns:
        Liste der neu aktivierten Einträge mit person_slug, filename
        und activated_at (ISO-Zeitstempel).

    Raises:
        FileNotFoundError: Wenn pool_root nicht existiert.
    """
    if not pool_root.is_dir():
        raise FileNotFoundError(f"Pool-Root nicht gefunden: {pool_root}")

    contract = load_proposal_contract(pool_root)
    reference_dir = pool_root / "reference"
    new_dir = pool_root / "new_faces"

    activated: list[dict[str, object]] = []

    if reference_dir.is_dir():
        known = {entry["filename"] for entry in contract.get("activated", [])}
        for candidate in sorted(reference_dir.glob("*.jpg")):
            if candidate.name not in known:
                entry: dict[str, object] = {
                    "person_slug": pool_root.name,
                    "filename": candidate.name,
                    "activated_at": _now_iso(),
                    "source": "manual_move",
                }
                contract.setdefault("activated", []).append(entry)
                activated.append(entry)

    if new_dir.is_dir():
        contract["remaining_new"] = sorted(
            f.name for f in new_dir.glob("*.jpg")
        )
    else:
        contract["remaining_new"] = []

    if activated:
        save_proposal_contract(pool_root, contract)

    return activated


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")
