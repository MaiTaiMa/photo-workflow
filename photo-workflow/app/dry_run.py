# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/dry_run.py
# PURPOSE:     Dry-Run-Planung und Report (AP4)
# AUTHOR:      Matzethias
# DATE:        2026-08-09
# VERSION:     1.0.0
# REQUIRES:    Python 3.8+, pool_sorting.py, naming_convention.py
# CHANGES:
#   2026-08-09: Initiale Implementierung für AP4
# =============================================================================


import json
import os
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path


# =============================================================================
# DryRunPlan-Klasse
# =============================================================================

class DryRunPlan:
    """
    Dry-Run-Plan für Pool-Rebuild.
    """
    
    def __init__(self, pool_type: str, base_dir: str):
        """
        Initialisiert Dry-Run-Plan.
        
        Args:
            pool_type: Typ des Pools (aesthetic, personal, face)
            base_dir: Basisverzeichnis
        """
        self.pool_type = pool_type
        self.base_dir = base_dir
        self.generated_at = datetime.utcnow().isoformat() + "Z"
        self.actions: List[Dict[str, Any]] = []
        self.warnings: List[str] = []
        self.errors: List[str] = []
    
    def add_action(self, action: str, current_path: str, planned_path: str, 
                   rank: int, nutzwert: float, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Fuegt Aktion zum Plan hinzu.
        
        Args:
            action: Aktionstyp (rename, move, delete, skip)
            current_path: Aktueller Pfad
            planned_path: Geplanter Pfad
            rank: Rang
            nutzwert: Nutzwert
            metadata: Optionale Metadaten
        """
        action_dict = {
            "action": action,
            "current_path": current_path,
            "planned_path": planned_path,
            "rank": rank,
            "nutzwert": round(nutzwert, 4),
        }
        
        if metadata:
            action_dict["metadata"] = metadata
        
        self.actions.append(action_dict)
    
    def add_warning(self, warning: str) -> None:
        """Fuegt Warnung hinzu."""
        self.warnings.append(warning)
    
    def add_error(self, error: str) -> None:
        """Fuegt Fehler hinzu."""
        self.errors.append(error)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Konvertiert Plan zu Dict.
        
        Returns:
            Dict-Repraesentation
        """
        return {
            "generated_at": self.generated_at,
            "pool_type": self.pool_type,
            "actions": self.actions,
            "warnings": self.warnings,
            "errors": self.errors,
            "summary": self.get_summary(),
        }
    
    def to_json(self, indent: int = 2) -> str:
        """
        Konvertiert Plan zu JSON-String.
        
        Returns:
            JSON-String
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Gibt Zusammenfassung zurueck.
        
        Returns:
            Dict mit Statistiken
        """
        rename_count = len([a for a in self.actions if a["action"] == "rename"])
        move_count = len([a for a in self.actions if a["action"] == "move"])
        delete_count = len([a for a in self.actions if a["action"] == "delete"])
        skip_count = len([a for a in self.actions if a["action"] == "skip"])
        
        return {
            "total_actions": len(self.actions),
            "rename_count": rename_count,
            "move_count": move_count,
            "delete_count": delete_count,
            "skip_count": skip_count,
            "warning_count": len(self.warnings),
            "error_count": len(self.errors),
        }


# =============================================================================
# Planung
# =============================================================================

def plan_renaming(images: List[Dict[str, Any]], pool_dir: str, base_dir: str,
                  rank_digits: int = 4, reference_date: Optional[str] = None) -> DryRunPlan:
    """
    Plant Umbenennungen für alle Bilder im Pool.
    
    Args:
        images: Liste von Bild-Entrys (aus selection.json)
        pool_dir: Pool-Verzeichnis
        base_dir: Basisverzeichnis
        rank_digits: Anzahl der Stellen für Rank
        reference_date: Referenzdatum für Nutzwert
    
    Returns:
        DryRunPlan mit allen geplanten Aktionen
    """
    plan = DryRunPlan(pool_type="unknown", base_dir=base_dir)
    
    # Importiere Pool-Sorting (AP4)
    try:
        from pool_sorting import reassign_ranks
    except ImportError:
        def reassign_ranks(images, rank_digits=4, reference_date=None):
            # Fallback: keine Sortierung
            for i, img in enumerate(images):
                img["rank"] = i + 1
            return images
    
    # Importiere Naming-Convention (AP4)
    try:
        from naming_convention import generate_target_path
    except ImportError:
        def generate_target_path(image, pool_dir, rank_digits=4):
            # Fallback: einfacher Dateiname
            rank = image.get("rank", 1)
            filename = f"{str(rank).zfill(rank_digits)}.jpg"
            return os.path.join(pool_dir, "reference", filename)
    
    # Ranks neu berechnen
    ranked_images = reassign_ranks(images, rank_digits, reference_date)
    
    # Existierende Dateien sammeln
    ref_dir = os.path.join(pool_dir, "reference")
    existing_files = set()
    if os.path.isdir(ref_dir):
        existing_files = set(os.listdir(ref_dir))
    
    # Für jedes Bild: geplanten Namen generieren
    for image in ranked_images:
        rel_path = image.get("rel_path", "")
        current_path = os.path.join(base_dir, rel_path)
        planned_path = generate_target_path(image, pool_dir, rank_digits)
        
        # Nutzwert
        nutzwert = image.get("_nutzwert", 0.5)
        
        # Kollision pruefen
        planned_filename = os.path.basename(planned_path)
        
        if planned_filename in existing_files:
            plan.add_warning(f"Kollision: {planned_filename} existiert bereits")
            plan.add_action("skip", current_path, planned_path, 
                           image.get("rank", 0), nutzwert,
                           {"reason": "Kollision"})
        else:
            plan.add_action("rename", current_path, planned_path,
                           image.get("rank", 0), nutzwert)
    
    return plan


# =============================================================================
# Report
# =============================================================================

def generate_report(plan: DryRunPlan, top_n: int = 10) -> str:
    """
    Generiert Text-Report für Dry-Run-Plan.
    
    Args:
        plan: DryRunPlan
        top_n: Anzahl Top-Bilder im Report
    
    Returns:
        Text-Report
    """
    lines = []
    
    # Header
    lines.append(f"Dry-Run Report für {plan.pool_type}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Datum: {plan.generated_at}")
    lines.append("")
    
    # Zusammenfassung
    summary = plan.get_summary()
    lines.append("Zusammenfassung:")
    lines.append(f"- Gesamte Aktionen: {summary['total_actions']}")
    lines.append(f"- Umbenennungen: {summary['rename_count']}")
    lines.append(f"- Verschiebungen: {summary['move_count']}")
    lines.append(f"- Loeschungen: {summary['delete_count']}")
    lines.append(f"- Uebersprungen: {summary['skip_count']}")
    lines.append(f"- Warnungen: {summary['warning_count']}")
    lines.append(f"- Fehler: {summary['error_count']}")
    lines.append("")
    
    # Top N Bilder
    lines.append(f"Top {top_n} Bilder:")
    rename_actions = [a for a in plan.actions if a["action"] == "rename"]
    for i, action in enumerate(rename_actions[:top_n]):
        filename = os.path.basename(action["planned_path"])
        lines.append(f"{i+1}. {filename} (nutzwert: {action['nutzwert']})")
    lines.append("")
    
    # Warnungen
    if plan.warnings:
        lines.append("Warnungen:")
        for warning in plan.warnings:
            lines.append(f"- {warning}")
        lines.append("")
    
    # Fehler
    if plan.errors:
        lines.append("Fehler:")
        for error in plan.errors:
            lines.append(f"- {error}")
        lines.append("")
    
    # Footer
    lines.append("=" * 60)
    lines.append("Ende des Reports")
    
    return "\n".join(lines)


# =============================================================================
# Hilfsfunktionen
# =============================================================================

def save_plan(plan: DryRunPlan, output_path: str) -> None:
    """
    Speichert Dry-Run-Plan als JSON.
    
    Args:
        plan: DryRunPlan
        output_path: Ausgabepfad
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(plan.to_json(indent=2))


def save_report(plan: DryRunPlan, output_path: str, top_n: int = 10) -> None:
    """
    Speichert Dry-Run-Report als Text.
    
    Args:
        plan: DryRunPlan
        output_path: Ausgabepfad
        top_n: Anzahl Top-Bilder
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    report = generate_report(plan, top_n)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)