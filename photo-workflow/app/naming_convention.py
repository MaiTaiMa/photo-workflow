"""
# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/naming_convention.py
# PURPOSE:     Dateinamen-Generierung nach Konvention (AP4)
# AUTHOR:      Benjamin (via AP4-Implementierung)
# DATE:        2026-08-09
# VERSION:     1.0.0 (AP4)
# REQUIRES:    Python 3.8+
# CHANGES:
#   2026-08-09: Initiale Implementierung für AP4
#               - format_rank() für dynamische Rang-Formatierung
#               - extract_original_stem() für Original-Stem
#               - compute_stable_suffix() für reproduzierbaren Hash
#               - generate_filename() für vollständigen Dateinamen
#               - validate_filename() für Kollisionspruefung
# =============================================================================
"""

import hashlib
import re
import os
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path


# =============================================================================
# Konstanten
# =============================================================================

DEFAULT_RANK_DIGITS = 4
SUFFIX_LENGTH = 12  # Zeichen für stable-suffix


# =============================================================================
# Rank-Formatierung
# =============================================================================

def format_rank(rank: int, rank_digits: int = DEFAULT_RANK_DIGITS) -> str:
    """
    Formatiert Rank als String mit fuehrenden Nullen.
    
    Args:
        rank: Rang (1, 2, 3, ...)
        rank_digits: Anzahl der Stellen (default: 4)
    
    Returns:
        Formatierter Rank (z.B. "0001", "0002", "0100", "1000")
    """
    if rank < 1:
        raise ValueError(f"rank muss >= 1 sein (ist: {rank})")
    
    if rank_digits < 1 or rank_digits > 10:
        raise ValueError(f"rank_digits muss zwischen 1 und 10 liegen (ist: {rank_digits})")
    
    max_rank = 10 ** rank_digits
    
    if rank >= max_rank:
        raise ValueError(f"rank {rank} ueberschreitet Maximum ({max_rank - 1}) bei rank_digits={rank_digits}")
    
    return str(rank).zfill(rank_digits)


# =============================================================================
# Original-Stem-Extraktion
# =============================================================================

def extract_original_stem(filename: str) -> str:
    """
    Extrahiert Original-Stem (erster Buchstabe) aus Dateiname.
    
    Args:
        filename: Dateiname (z.B. "IMG_20230809_123456.JPG")
    
    Returns:
        Erster Buchstabe (A-Z, fallback: "A")
    """
    # Stem ohne Extension
    stem = Path(filename).stem
    
    # Ersten alphanumerischen Buchstaben finden
    match = re.search(r'[A-Za-z]', stem)
    
    if match:
        return match.group().upper()
    else:
        # Fallback: "A"
        return "A"


# =============================================================================
# Stable-Suffix-Berechnung
# =============================================================================

def compute_stable_suffix(image: Dict[str, Any]) -> str:
    """
    Berechnet stabilen Suffix (12 Zeichen) für ein Bild.
    
    Args:
        image: Bild-Entry (mit rel_path, score, added_at, etc.)
    
    Returns:
        SHA-256 Hash (erste 12 Zeichen)
    """
    # Quellen für Hash
    components = [
        image.get("rel_path", ""),
        str(image.get("score", 0)),
        image.get("added_at", ""),
        image.get("source", ""),
    ]
    
    # Kanonische Darstellung
    canonical = "|".join(components)
    
    # SHA-256
    hash_hex = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    
    # Erste 12 Zeichen
    return hash_hex[:SUFFIX_LENGTH]


# =============================================================================
# Dateinamen-Generierung
# =============================================================================

def generate_filename(image: Dict[str, Any], rank_digits: int = DEFAULT_RANK_DIGITS) -> str:
    """
    Generiert vollständigen Dateinamen nach Konvention.
    
    Format: <rank>__<original-stem>__<stable-suffix><extension>
    
    Args:
        image: Bild-Entry (mit rel_path, rank, etc.)
        rank_digits: Anzahl der Stellen für Rank
    
    Returns:
        Vollstä¨¤ndiger Dateiname (z.B. "0001__A__abc123def45.JPG")
    """
    # Rank
    rank = image.get("rank", 1)
    rank_str = format_rank(rank, rank_digits)
    
    # Original-Stem
    rel_path = image.get("rel_path", "")
    original_filename = os.path.basename(rel_path)
    original_stem = extract_original_stem(original_filename)
    
    # Stable-Suffix
    stable_suffix = compute_stable_suffix(image)
    
    # Extension
    extension = Path(original_filename).suffix.upper()
    if not extension:
        extension = ".JPG"  # Fallback
    
    # Vollstä¨¤ndiger Dateiname
    filename = f"{rank_str}__{original_stem}__{stable_suffix}{extension}"
    
    return filename


def generate_target_path(image: Dict[str, Any], pool_dir: str, 
                         rank_digits: int = DEFAULT_RANK_DIGITS) -> str:
    """
    Generiert vollständigen Ziel-Pfad für ein Bild.
    
    Args:
        image: Bild-Entry
        pool_dir: Pool-Verzeichnis (z.B. "WORKFLOW_DATA/samples/aesthetic_reference")
        rank_digits: Anzahl der Stellen für Rank
    
    Returns:
        Vollstä¨¤ndiger Ziel-Pfad
    """
    filename = generate_filename(image, rank_digits)
    target_path = os.path.join(pool_dir, "reference", filename)
    return target_path


# =============================================================================
# Kollisionspruefung
# =============================================================================

def validate_filename(generated_filename: str, existing_files: List[str]) -> Tuple[bool, List[str]]:
    """
    Validiert generierten Dateinamen auf Kollisionen.
    
    Args:
        generated_filename: Generierter Dateiname
        existing_files: Liste existierender Dateinamen
    
    Returns:
        Tuple (is_valid, errors)
    """
    errors = []
    
    # Kollision mit existierenden Dateien
    if generated_filename in existing_files:
        errors.append(f"Kollision: {generated_filename} existiert bereits")
        return False, errors
    
    # Ungueltige Zeichen
    if not re.match(r'^[A-Za-z0-9_\-\.]+$', generated_filename):
        errors.append(f"Ungueltige Zeichen in {generated_filename}")
        return False, errors
    
    return True, errors


def check_path_collisions(planned_paths: List[str], base_dir: str) -> Tuple[bool, List[str]]:
    """
    Prueft Pfad-Kollisionen und Sicherheit.
    
    Args:
        planned_paths: Geplante Zielpfade
        base_dir: Basisverzeichnis
    
    Returns:
        Tuple (is_valid, errors)
    """
    errors = []
    
    # Importiere Pfadvalidierung (AP2)
    try:
        from runtime_paths import is_path_within_base
    except ImportError:
        def is_path_within_base(path: str, base: str) -> bool:
            return '..' not in path and path.startswith(base)
    
    # Jede Pfad pruefen
    for path in planned_paths:
        # Existiert bereits?
        if os.path.exists(path):
            errors.append(f"Kollision: {path} existiert bereits")
        
        # Innerhalb von base_dir?
        if not is_path_within_base(path, base_dir):
            errors.append(f"Unsicherer Pfad: {path} liegt außerhalb von {base_dir}")
    
    return len(errors) == 0, errors