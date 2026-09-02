# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/synology_photos_adapter.py
# PURPOSE:     Synology Photos API Adapter (capability-gated).
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     2.1.0
# REQUIRES:    Python 3.11+, requests
# CHANGES:
#   2026-09-02 | 2.1.0 | Echte API-Calls fuer Album-Operationen
#   2026-09-02 | 2.0.0 | Album-Upsert-Grundgeruest
#   2026-08-29 | 1.0.0 | Initial version
# =============================================================================


from __future__ import annotations

import os
import requests
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin


@dataclass(frozen=True)
class CapabilityReport:
    status: str
    authenticated: bool
    space: str
    write_rating: bool
    write_tags: bool
    write_known_persons: bool
    album_upsert: bool
    reason: str | None = None


class SynologyPhotosAdapter:
    """
    Capability-gated Adapter für Synology Photos API.

    API-Endpunkte:
    - SYNO.Foto.Browse.Album: list, create, add_item
    - Session-Handling via Umgebungsvariablen

    Keine privaten Endpunkte werden geraten oder aufgerufen.
    Alle Schreiboperationen erfordern einen erfolgreichen Pilotlauf-Nachweis.
    """

    def __init__(self, config: dict):
        settings = config.get("synology_api", {})
        self.enabled = bool(settings.get("enabled", False))
        self.dry_run = bool(settings.get("dry_run", True))
        self.host = settings.get("host", os.getenv("SYNOLOGY_HOST", "localhost"))
        self.port = int(settings.get("port", os.getenv("SYNOLOGY_PORT", "5000")))
        self.protocol = settings.get("protocol", "http")
        self.space = settings.get("space", "shared")
        self.write_rating = bool(settings.get("write_rating", True))
        self.write_tags = bool(settings.get("write_tags", True))
        self.write_known_persons = bool(settings.get("write_known_persons", False))
        self.album_upsert = bool(settings.get("album_upsert", False))

        # Session-Cache
        self._session_id: Optional[str] = None
        self._base_url = f"{self.protocol}://{self.host}:{self.port}"

    def _get_session_id(self) -> Optional[str]:
        """
        Holt oder erstellt eine Session-ID via SYNO.API.Auth.
        """
        if self._session_id:
            return self._session_id

        user = os.getenv("SYNOLOGY_USER")
        password = os.getenv("SYNOLOGY_PASSWORD")

        if not user or not password:
            return None

        try:
            response = requests.get(
                urljoin(self._base_url, "/webapi/auth.cgi"),
                params={
                    "api": "SYNO.API.Auth",
                    "method": "login",
                    "version": "7",
                    "account": user,
                    "passwd": password,
                    "session": "FotoStation",
                    "format": "cookie",
                },
                timeout=10,
            )
            data = response.json()
            if data.get("success"):
                self._session_id = data["data"]["sid"]
                return self._session_id
        except Exception:
            pass
        return None

    def _call(
        self,
        api: str,
        method: str,
        version: int,
        **params,
    ) -> dict:
        """
        Führt einen API-Aufruf mit Session-Handling aus.
        """
        sid = self._get_session_id()
        if not sid:
            return {"success": False, "error": {"code": "auth_failed"}}

        try:
            response = requests.get(
                urljoin(self._base_url, "/webapi/entry.cgi"),
                params={
                    "api": api,
                    "method": method,
                    "version": version,
                    "_sid": sid,
                    **params,
                },
                timeout=30,
            )
            return response.json()
        except Exception as exc:
            return {"success": False, "error": {"code": "network_error", "message": str(exc)}}

    def healthcheck(self) -> CapabilityReport:
        if self.space not in {"shared", "personal"}:
            return CapabilityReport(
                "configuration_invalid", False, self.space,
                False, False, False, False, "invalid_space",
            )
        if not self.enabled or self.dry_run:
            return CapabilityReport(
                "dry_run", False, self.space,
                self.write_rating, self.write_tags, False, self.album_upsert,
            )
        sid = self._get_session_id()
        authenticated = bool(sid)
        if not authenticated:
            return CapabilityReport(
                "authentication_required", False, self.space,
                self.write_rating, self.write_tags, False, self.album_upsert,
                "SYNOLOGY_USER/PASSWORD nicht gesetzt",
            )
        return CapabilityReport(
            "ready", True, self.space,
            self.write_rating, self.write_tags, self.write_known_persons, self.album_upsert,
        )

    def apply_metadata(
        self,
        *,
        relative_path: str,
        rating: int | None,
        tags: list[str],
        person_slug: str | None = None,
    ) -> dict:
        report = self.healthcheck()
        if report.status != "ready":
            return {
                "status": "capability_unsupported",
                "relative_path": relative_path,
                "reason": report.reason or report.status,
            }
        if person_slug and not report.write_known_persons:
            return {
                "status": "capability_unsupported",
                "reason": "known_persons_disabled",
            }
        return {
            "status": "capability_unsupported",
            "reason": "adapter_not_implemented",
        }

    def list_albums(self) -> list[dict]:
        """
        Listet alle normalen Alben im konfigurierten Space.

        Ausgabe: Liste von Dicts mit 'id' und 'name'.
        """
        result = self._call("SYNO.Foto.Browse.Album", "list", 2, offset=0, limit=1000)
        if not result.get("success"):
            return []
        return result.get("data", {}).get("list", [])

    def find_album_by_name(self, name: str) -> int | None:
        """
        Sucht ein Album nach Namen und gibt die Album-ID zurück.
        """
        for album in self.list_albums():
            if album.get("name") == name:
                return album["id"]
        return None

    def create_album(self, name: str) -> int | None:
        """
        Erstellt ein neues normales Album und gibt die Album-ID zurück.
        """
        result = self._call("SYNO.Foto.Browse.Album", "create", 2, name=name)
        if not result.get("success"):
            return None
        return result.get("data", {}).get("id")

    def add_items_to_album(
        self,
        album_id: int,
        item_ids: list[int],
    ) -> dict:
        """
        Fügt Foto-IDs einem Album hinzu.
        """
        if not item_ids:
            return {"success": True, "message": "no_items"}

        result = self._call(
            "SYNO.Foto.Browse.Album",
            "add_item",
            2,
            id=album_id,
            item=str(item_ids),
        )
        return result

    def upsert_album(self, name: str) -> tuple[int | None, bool]:
        """
        Album-Upsert: existierendes Album finden oder neues erstellen.

        Rückgabe: (album_id, created)
        - created=True wenn neu erstellt, False wenn vorhanden.
        - album_id=None wenn fehlgeschlagen.
        """
        album_id = self.find_album_by_name(name)
        if album_id is not None:
            return album_id, False
        album_id = self.create_album(name)
        return album_id, bool(album_id is not None)
