"""
# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/score_integration.py
# PURPOSE:     Integration von CLIP-Scores mit existing scores (AP6)
# AUTHOR:      Benjamin (via AP6-Implementierung)
# DATE:        2026-08-09
# VERSION:     1.0.0 (AP6)
# REQUIRES:    Python 3.8+, clip_scorer.py
# CHANGES:
#   2026-08-09: Initiale Implementierung für AP6
#               - compute_final_score() für Score-Kombination
#               - integrate_clip_scores() für Batch-Integration
#               - validate_scores() für Score-Validierung
# =============================================================================
"""

from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
import os


# =============================================================================
# Score-Kombination
# =============================================================================

def compute_final_score(generic_score: float, aesthetic_score: float,
                        personal_score: float,
                        weights: Optional[Dict[str, float]] = None) -> float:
    """
    Berechnet finalen Score aus 3 Komponenten.
    
    Args:
        generic_score: Allgemeiner Score (0-1)
        aesthetic_score: Aesthetic-Reference-Score (0-1)
        personal_score: Personal-Training-Score (0-1)
        weights: Gewichtung (default: generic=0.3, aesthetic=0.3, personal=0.4)
    
    Returns:
        Finaler Score (0-1)
    """
    if weights is None:
        weights = {
            "generic": 0.3,
            "aesthetic": 0.3,
            "personal": 0.4,
        }
    
    # Gewichteter Durchschnitt
    final_score = (
        generic_score * weights["generic"] +
        aesthetic_score * weights["aesthetic"] +
        personal_score * weights["personal"]
    )
    
    return min(1.0, max(0.0, final_score))


def integrate_clip_scores(images: List[Dict[str, Any]], 
                          model_path: str,
                          aesthetic_references: List[str],
                          personal_references: List[str],
                          shadow_mode: bool = True,
                          weights: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
    """
    Integriert CLIP-Scores in Bilder.
    
    Args:
        images: Liste von Bild-Entrys
        model_path: Pfad zum CLIP-Modell
        aesthetic_references: Liste von aesthetic-Referenzpfaden
        personal_references: Liste von personal-Referenzpfaden
        shadow_mode: Shadow-Mode (nur Logging)
        weights: Gewichtung
    
    Returns:
        Bilder mit CLIP-Scores
    """
    # Importiere CLIP-Scorer
    try:
        from clip_scorer import CLIPScorer
    except ImportError:
        # Fallback: keine CLIP-Scores
        for image in images:
            image["aesthetic_reference_score"] = 0.5
            image["personal_score"] = 0.5
            image["final_score"] = 0.5
        return images
    
    # Scorer initialisieren
    scorer = CLIPScorer(model_path, local_files_only=True, shadow_mode=shadow_mode)
    
    # Für jedes Bild: CLIP-Scores berechnen
    for image in images:
        rel_path = image.get("rel_path", "")
        image_path = rel_path  # Annahme: rel_path ist vollständiger Pfad
        
        # Aesthetic-Score
        aesthetic_score = scorer.compute_aesthetic_score(image_path, aesthetic_references)
        image["aesthetic_reference_score"] = aesthetic_score
        image["aesthetic_reference_score_source"] = "clip_aesthetic"
        
        # Personal-Score
        personal_score = scorer.compute_personal_score(image_path, personal_references)
        image["personal_score"] = personal_score
        image["personal_score_source"] = "clip_personal"
        
        # Generic-Score (existing oder Fallback)
        generic_score = image.get("score", 0.5)
        image["generic_score"] = generic_score
        
        # Finaler Score
        final_score = compute_final_score(generic_score, aesthetic_score, personal_score, weights)
        image["final_score"] = final_score
    
    return images


# =============================================================================
# Score-Validierung
# =============================================================================

def validate_scores(images: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """
    Validiert Scores in Bildern.
    
    Args:
        images: Liste von Bild-Entrys
    
    Returns:
        Tuple (is_valid, warnings)
    """
    warnings = []
    is_valid = True
    
    for i, image in enumerate(images):
        # Scores prüfen
        for score_key in ["generic_score", "aesthetic_reference_score", "personal_score", "final_score"]:
            if score_key in image:
                score = image[score_key]
                
                # Typ prüfen
                if not isinstance(score, (int, float)):
                    warnings.append(f"images[{i}].{score_key} muss eine Zahl sein")
                    is_valid = False
                
                # Bereich prüfen (0-1)
                elif score < 0 or score > 1:
                    warnings.append(f"images[{i}].{score_key} muss zwischen 0 und 1 liegen (ist: {score})")
                    is_valid = False
        
        # Sources prüfen
        for source_key in ["generic_score_source", "aesthetic_reference_score_source", "personal_score_source"]:
            if source_key in image:
                source = image[source_key]
                if not isinstance(source, str):
                    warnings.append(f"images[{i}].{source_key} muss ein String sein")
    
    return is_valid, warnings


# =============================================================================
# Shadow-Mode-Reporting
# =============================================================================

def generate_shadow_report(images: List[Dict[str, Any]], 
                           original_images: List[Dict[str, Any]]) -> str:
    """
    Generiert Report für Shadow-Mode-Vergleich.
    
    Args:
        images: Bilder mit CLIP-Scores
        original_images: Originale Bilder (ohne CLIP)
    
    Returns:
        Text-Report
    """
    lines = []
    lines.append("Shadow-Mode Report: CLIP-Score-Vergleich")
    lines.append("=" * 60)
    lines.append("")
    
    # Für jedes Bild: Vergleich
    for i, (image, orig) in enumerate(zip(images[:10], original_images[:10])):
        orig_score = orig.get("score", 0.5)
        final_score = image.get("final_score", 0.5)
        
        diff = final_score - orig_score
        
        lines.append(f"{i+1}. {image.get('rel_path', 'unknown')}")
        lines.append(f"   Original: {orig_score:.3f}")
        lines.append(f"   Mit CLIP: {final_score:.3f}")
        lines.append(f"   Diff: {diff:+.3f}")
        lines.append("")
    
    lines.append("=" * 60)
    
    return "\n".join(lines)