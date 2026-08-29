# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/best_of_selection.py
# PURPOSE:     Best-of-Auswahl für Serien (AP7)
# AUTHOR:      Matzethias
# DATE:        2026-08-09
# VERSION:     1.0.0
# REQUIRES:    Python 3.8+, series_detection.py
# CHANGES:
#   2026-08-09: Initiale Implementierung für AP7
# =============================================================================


from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from app.series_detection import Series


# =============================================================================
# Dataclasses
# =============================================================================

@dataclass
class SelectionResult:
    """Ergebnis der Best-of-Auswahl."""
    series_id: str
    selected_images: List[Dict[str, Any]]
    rejected_images: List[Dict[str, Any]]
    protected_images: List[Dict[str, Any]]
    reasons: Dict[str, str]  # rel_path -> reason


# =============================================================================
# Score-Berechnung
# =============================================================================

def compute_best_of_score(image: Dict[str, Any]) -> float:
    """
    Berechnet best_of_score für ein Bild.
    
    Args:
        image: Bild-Entry
    
    Returns:
        best_of_score (0-1)
    """
    # Komponenten
    sharpness = image.get("sharpness_score", 0.5)
    exposure = image.get("exposure_score", 0.5)
    faces = image.get("face_score", 0.5)
    aesthetics = image.get("aesthetic_score", 0.5)
    uniqueness = image.get("uniqueness_score", 0.5)
    
    # Gewichteter Durchschnitt
    score = (
        sharpness * 0.3 +
        exposure * 0.2 +
        faces * 0.2 +
        aesthetics * 0.2 +
        uniqueness * 0.1
    )
    
    return min(1.0, max(0.0, score))


# =============================================================================
# Best-of-Auswahl
# =============================================================================

def select_best_of(series: Series, 
                   max_selections: int = 3,
                   min_score: float = 0.3) -> SelectionResult:
    """
    Waehlt beste Bilder aus Serie aus.
    
    Args:
        series: Serie
        max_selections: Maximale Anzahl auszuwaelender Bilder (default: 3)
        min_score: Mindest-Score für Auswahl (default: 0.3)
    
    Returns:
        SelectionResult
    """
    selected = []
    rejected = []
    protected = []
    reasons = {}
    
    # Scores berechnen
    for image in series.images:
        score = compute_best_of_score(image)
        image["best_of_score"] = score
    
    # Geschuetzte Bilder identifizieren
    protected = get_protected_images(series.images)
    protected_paths = set(img.get("rel_path") for img in protected)
    
    # Nach Score sortieren
    sorted_images = sorted(series.images, key=lambda x: -x.get("best_of_score", 0))
    
    # Beste auswaehlen
    for i, image in enumerate(sorted_images):
        rel_path = image.get("rel_path", "")
        score = image.get("best_of_score", 0)
        
        # Geschuetzte Bilder immer behalten
        if rel_path in protected_paths:
            if image not in selected:
                selected.append(image)
                reasons[rel_path] = "Geschuetzt (user_rating, MANUAL_KEEP, etc.)"
            continue
        
        # Maximalanzahl erreichen
        if len(selected) >= max_selections:
            rejected.append(image)
            reasons[rel_path] = f"Maximale Auswahl erreicht ({max_selections})"
            continue
        
        # Mindest-Score
        if score < min_score:
            rejected.append(image)
            reasons[rel_path] = f"Score zu niedrig ({score:.2f} < {min_score})"
            continue
        
        # Auswaehlen
        selected.append(image)
        
        if i == 0:
            reasons[rel_path] = f"Bestes Bild (Score: {score:.2f})"
        else:
            reasons[rel_path] = f"Rank {i+1} (Score: {score:.2f})"
    
    # Rest ablehnen
    selected_paths = set(img.get("rel_path") for img in selected)
    for image in series.images:
        rel_path = image.get("rel_path", "")
        if rel_path not in selected_paths and image not in rejected and image not in protected:
            rejected.append(image)
            reasons[rel_path] = "Nicht ausgewählt"
    
    return SelectionResult(
        series_id=series.series_id,
        selected_images=selected,
        rejected_images=rejected,
        protected_images=protected,
        reasons=reasons,
    )


# =============================================================================
# Geschuetzte Bilder
# =============================================================================

def get_protected_images(images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Identifiziert geschuetzte Bilder.
    
    Args:
        images: Liste von Bildern
    
    Returns:
        Liste von geschuetzten Bildern
    """
    protected = []
    
    for image in images:
        is_protected = False
        reason = None
        
        # 1. user_rating >= 4 Sterne
        user_rating = image.get("user_rating", 0)
        if user_rating >= 4:
            is_protected = True
            reason = f"user_rating={user_rating} Sterne"
        
        # 2. MANUAL_KEEP (Pfad enthält MANUAL_KEEP)
        rel_path = image.get("rel_path", "")
        if "MANUAL_KEEP" in rel_path:
            is_protected = True
            reason = "MANUAL_KEEP"
        
        # 3. metadata.protected = true
        metadata = image.get("metadata", {})
        if metadata.get("protected", False):
            is_protected = True
            reason = "metadata.protected=true"
        
        if is_protected:
            protected.append(image)
            image["_protected_reason"] = reason
    
    return protected


# =============================================================================
# Review-Pflicht
# =============================================================================

def needs_review(series: Series, selection: SelectionResult) -> bool:
    """
    Prueft, ob Serie Review-Pflicht hat.
    
    Args:
        series: Serie
        selection: Auswahl-Ergebnis
    
    Returns:
        True, wenn Review erforderlich
    """
    # 1. Serien mit size > 10
    if series.size > 10:
        return True
    
    # 2. Serien mit best_of_score < 0.5 (alle schlecht)
    max_score = max(img.get("best_of_score", 0) for img in series.images)
    if max_score < 0.5:
        return True
    
    # 3. Serien mit Gesichts-Erkennung
    for image in series.images:
        if image.get("face_detected", False):
            return True
    
    return False