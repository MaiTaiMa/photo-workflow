"""
# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/series_report.py
# PURPOSE:     Report-Generierung für Serien (AP7)
# AUTHOR:      Benjamin (via AP7-Implementierung)
# DATE:        2026-08-09
# VERSION:     1.0.0 (AP7)
# REQUIRES:    Python 3.8+, series_detection.py, best_of_selection.py
# CHANGES:
#   2026-08-09: Initiale Implementierung für AP7
#               - generate_series_report() für JSON-Report
#               - generate_text_report() für Text-Report
#               - save_report() für Speichern
# =============================================================================
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from series_detection import Series
from best_of_selection import SelectionResult


# =============================================================================
# Report-Generierung
# =============================================================================

def generate_series_report(series: Series, selection: SelectionResult) -> Dict[str, Any]:
    """
    Generiert JSON-Report für Serie.
    
    Args:
        series: Serie
        selection: Auswahl-Ergebnis
    
    Returns:
        Report als Dict
    """
    # Selection
    selected = []
    for img in selection.selected_images:
        selected.append({
            "rel_path": img.get("rel_path", ""),
            "rank": img.get("best_of_score", 0),
            "best_of_score": round(img.get("best_of_score", 0), 3),
            "reason": selection.reasons.get(img.get("rel_path", ""), ""),
        })
    
    # Rejection
    rejected = []
    for img in selection.rejected_images:
        rejected.append({
            "rel_path": img.get("rel_path", ""),
            "reason": selection.reasons.get(img.get("rel_path", ""), ""),
        })
    
    # Protected
    protected = []
    for img in selection.protected_images:
        protected.append({
            "rel_path": img.get("rel_path", ""),
            "reason": img.get("_protected_reason", "Geschuetzt"),
        })
    
    # Report
    report = {
        "series_id": series.series_id,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_images": series.size,
        "selected_count": len(selection.selected_images),
        "rejected_count": len(selection.rejected_images),
        "protected_count": len(selection.protected_images),
        "series_start_time": series.start_time.isoformat() if series.start_time else None,
        "series_end_time": series.end_time.isoformat() if series.end_time else None,
        "selection": selected,
        "rejection": rejected,
        "protected": protected,
    }
    
    return report


def generate_text_report(series: Series, selection: SelectionResult) -> str:
    """
    Generiert Text-Report für Serie.
    
    Args:
        series: Serie
        selection: Auswahl-Ergebnis
    
    Returns:
        Text-Report
    """
    lines = []
    
    # Header
    lines.append(f"Serien-Report: {series.series_id}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Generiert: {datetime.utcnow().isoformat()}Z")
    lines.append(f"Zeitraum: {series.start_time} bis {series.end_time}")
    lines.append(f"Anzahl Bilder: {series.size}")
    lines.append("")
    
    # Zusammenfassung
    lines.append("Zusammenfassung:")
    lines.append(f"- Ausgewaehlt: {len(selection.selected_images)}")
    lines.append(f"- Abgelehnt: {len(selection.rejected_images)}")
    lines.append(f"- Geschuetzt: {len(selection.protected_images)}")
    lines.append("")
    
    # Ausgewaehlt
    lines.append("Ausgewaehlt:")
    for i, img in enumerate(selection.selected_images, 1):
        rel_path = img.get("rel_path", "")
        score = img.get("best_of_score", 0)
        reason = selection.reasons.get(rel_path, "")
        lines.append(f"  {i}. {rel_path}")
        lines.append(f"     Score: {score:.3f}")
        lines.append(f"     Grund: {reason}")
    lines.append("")
    
    # Abgelehnt
    if selection.rejected_images:
        lines.append("Abgelehnt:")
        for img in selection.rejected_images[:5]:  # Max 5 anzeigen
            rel_path = img.get("rel_path", "")
            reason = selection.reasons.get(rel_path, "")
            lines.append(f"  - {rel_path}")
            lines.append(f"    Grund: {reason}")
        if len(selection.rejected_images) > 5:
            lines.append(f"  ... und {len(selection.rejected_images) - 5} weitere")
        lines.append("")
    
    # Geschuetzt
    if selection.protected_images:
        lines.append("Geschuetzt:")
        for img in selection.protected_images:
            rel_path = img.get("rel_path", "")
            reason = img.get("_protected_reason", "Geschuetzt")
            lines.append(f"  - {rel_path}")
            lines.append(f"    Grund: {reason}")
        lines.append("")
    
    # Footer
    lines.append("=" * 60)
    lines.append("Ende des Reports")
    
    return "\n".join(lines)


# =============================================================================
# Speichern
# =============================================================================

def save_report(report: Dict[str, Any], output_path: str) -> None:
    """
    Speichert JSON-Report.
    
    Args:
        report: Report als Dict
        output_path: Ausgabepfad
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)


def save_text_report(text_report: str, output_path: str) -> None:
    """
    Speichert Text-Report.
    
    Args:
        text_report: Text-Report
        output_path: Ausgabepfad
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text_report)