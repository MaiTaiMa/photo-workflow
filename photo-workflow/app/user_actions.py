# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/user_actions.py
# PURPOSE:     User-Action-Generierung und Report (AP5)
# AUTHOR:      Matzethias
# DATE:        2026-08-09
# VERSION:     1.0.0
# REQUIRES:    Python 3.8+, pool_limits.py
# CHANGES:
#   2026-08-09: Initiale Implementierung für AP5
#               - UserAction-Klasse für Actions
#               - UserActionReport-Klasse für Reports
#               - generate_user_actions() für Action-Generierung
#               - get_suggested_actions() für Vorschlaege
# =============================================================================


from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json


# =============================================================================
# Dataclasses
# =============================================================================

@dataclass
class UserAction:
    """Eine User-Action."""
    action_type: str  # activate, remove, review, unblock
    description: str
    suggested_paths: List[str] = field(default_factory=list)
    reason: str = ""
    priority: int = 1  # 1 = hoch, 5 = niedrig
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action_type,
            "description": self.description,
            "suggested_paths": self.suggested_paths,
            "reason": self.reason,
            "priority": self.priority,
            "metadata": self.metadata,
        }


@dataclass
class UserActionReport:
    """Report für User-Actions."""
    generated_at: str
    pool_type: str
    user_actions_required: bool
    actions: List[UserAction] = field(default_factory=list)
    blocker: Optional[Dict[str, Any]] = None
    summary: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "pool_type": self.pool_type,
            "user_actions_required": self.user_actions_required,
            "actions": [a.to_dict() for a in self.actions],
            "blocker": self.blocker,
            "summary": self.summary,
        }
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# =============================================================================
# User-Action-Generierung
# =============================================================================

def generate_user_actions(pool_type: str, active_count: int, new_count: int,
                          limits: Dict[str, int], images: List[Dict[str, Any]]) -> UserActionReport:
    """
    Generiert User-Actions basierend auf Limit-Status.
    
    Args:
        pool_type: Typ des Pools (aesthetic, personal, face)
        active_count: Anzahl aktiver Bilder
        new_count: Anzahl neuer Vorschlaege
        limits: Limits-Dict
        images: Alle Bilder im Pool
    
    Returns:
        UserActionReport
    """
    now = datetime.utcnow().isoformat() + "Z"
    report = UserActionReport(
        generated_at=now,
        pool_type=pool_type,
        user_actions_required=False,
    )
    
    max_active = limits.get("max_active", 100)
    min_active = limits.get("min_active", 50)
    target_active = limits.get("target_active", 80)
    max_new = limits.get("max_new", 50)
    
    # 1. min_active unterschritten?
    if active_count < min_active:
        report.user_actions_required = True
        
        # Vorschlag: neue Bilder aus new aktivieren
        new_images = [img for img in images if img.get("status") == "new"]
        new_images_sorted = sorted(new_images, key=lambda x: x.get("rank", 9999))
        
        needed = min_active - active_count
        suggested_paths = [img.get("rel_path") for img in new_images_sorted[:needed]]
        
        report.actions.append(UserAction(
            action_type="activate",
            description=f"Aktiviere {needed} Vorschlaege aus new_refs/new_faces",
            suggested_paths=suggested_paths,
            reason=f"min_active unterschritten: {active_count} < {min_active}",
            priority=1,  # Hoch
            metadata={"needed": needed, "current": active_count, "min": min_active},
        ))
    
    # 2. max_active erreicht?
    if active_count >= max_active:
        report.user_actions_required = True
        
        # Vorschlag: alte Bilder entfernen
        active_images = [img for img in images if img.get("status") == "active"]
        active_images_sorted = sorted(active_images, key=lambda x: -x.get("rank", 0))  # Hoechste ranks zuerst
        
        # Top 10 mit hoechsten ranks (schlechteste)
        suggested_paths = [img.get("rel_path") for img in active_images_sorted[:10]]
        
        report.actions.append(UserAction(
            action_type="remove",
            description=f"Entferne alte Referenzen um Platz zu schaffen",
            suggested_paths=suggested_paths,
            reason=f"max_active erreicht: {active_count} >= {max_active}",
            priority=1,  # Hoch
            metadata={"current": active_count, "max": max_active},
        ))
        
        # Blocker setzen
        report.blocker = {
            "type": "max_active_reached",
            "message": f"Pool ist voll ({active_count}/{max_active}). Bitte Referenzen entfernen.",
        }
    
    # 3. max_new erreicht?
    if new_count >= max_new:
        report.user_actions_required = True
        
        # Vorschlag: neue Vorschlaege aktivieren oder entfernen
        new_images = [img for img in images if img.get("status") == "new"]
        new_images_sorted = sorted(new_images, key=lambda x: -x.get("score", 0))  # Beste Scores zuerst
        
        # Top 10 mit besten Scores
        suggested_activate = [img.get("rel_path") for img in new_images_sorted[:10]]
        
        report.actions.append(UserAction(
            action_type="activate",
            description=f"Aktiviere beste Vorschlaege aus new_refs/new_faces",
            suggested_paths=suggested_activate,
            reason=f"max_new erreicht: {new_count} >= {max_new}",
            priority=2,  # Mittel
            metadata={"current": new_count, "max": max_new},
        ))
        
        # Blocker setzen (wenn nicht schon gesetzt)
        if report.blocker is None:
            report.blocker = {
                "type": "max_new_reached",
                "message": f"New-Queue ist voll ({new_count}/{max_new}). Bitte Vorschlaege aktivieren oder entfernen.",
            }
    
    # Summary
    report.summary = {
        "active_count": active_count,
        "new_count": new_count,
        "max_active": max_active,
        "min_active": min_active,
        "target_active": target_active,
        "max_new": max_new,
        "action_count": len(report.actions),
    }
    
    return report


def get_suggested_actions(report: UserActionReport, max_actions: int = 5) -> List[UserAction]:
    """
    Gibt empfohlene User-Actions zurueck (sortiert nach Prioritaet).
    
    Args:
        report: UserActionReport
        max_actions: Maximale Anzahl zurueckgegebener Actions
    
    Returns:
        Liste von UserActions (sortiert nach priority)
    """
    # Sortiere nach priority (1 = hoch)
    sorted_actions = sorted(report.actions, key=lambda x: x.priority)
    
    return sorted_actions[:max_actions]


# =============================================================================
# Hilfsfunktionen
# =============================================================================

def save_user_actions_report(report: UserActionReport, output_path: str) -> None:
    """
    Speichert User-Action-Report als JSON.
    
    Args:
        report: UserActionReport
        output_path: Ausgabepfad
    """
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report.to_json(indent=2))