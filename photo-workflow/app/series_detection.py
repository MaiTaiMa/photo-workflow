# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/series_detection.py
# PURPOSE:     Serien-Erkennung (AP7)
# AUTHOR:      Matzethias
# DATE:        2026-08-09
# VERSION:     1.0.0
# REQUIRES:    Python 3.8+, datetime
# CHANGES:
#   2026-08-09: Initiale Implementierung für AP7
#               - detect_series() für Zeit-basierte Erkennung
#               - cluster_by_similarity() für visuelle Aehnlichkeit
#               - Series-Klasse für Serien-Daten
# =============================================================================


from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass, field
import hashlib


# =============================================================================
# Dataclasses
# =============================================================================

@dataclass
class Series:
    """Eine Serie von Bildern."""
    series_id: str
    images: List[Dict[str, Any]] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def size(self) -> int:
        return len(self.images)
    
    @property
    def duration_seconds(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


# =============================================================================
# Serien-Erkennung
# =============================================================================

def detect_series(images: List[Dict[str, Any]], 
                  max_time_gap_seconds: int = 60,
                  min_series_size: int = 2,
                  max_series_size: int = 20) -> List[Series]:
    """
    Erkennt Serien basierend auf Zeit-Metadaten.
    
    Args:
        images: Liste von Bild-Entrys (mit datetime_original)
        max_time_gap_seconds: Max. Zeit zwischen Bildern (default: 60s)
        min_series_size: Mindestgroesse für Serie (default: 2)
        max_series_size: Maximalgroesse (default: 20)
    
    Returns:
        Liste von Series-Objekten
    """
    if not images:
        return []
    
    # Nach Zeit sortieren
    def get_datetime(img: Dict[str, Any]) -> datetime:
        dt_str = img.get("datetime_original", "")
        if dt_str:
            try:
                return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass
        return datetime.min
    
    sorted_images = sorted(images, key=get_datetime)
    
    # Serien bilden
    series_list = []
    current_series_images = [sorted_images[0]]
    
    for i in range(1, len(sorted_images)):
        prev_img = sorted_images[i - 1]
        curr_img = sorted_images[i]
        
        prev_dt = get_datetime(prev_img)
        curr_dt = get_datetime(curr_img)
        
        time_gap = (curr_dt - prev_dt).total_seconds()
        
        # Neue Serie wenn Gap zu gross oder max_series_size erreicht
        if time_gap > max_time_gap_seconds or len(current_series_images) >= max_series_size:
            # Aktuelle Serie abschliessen
            if len(current_series_images) >= min_series_size:
                series = create_series_from_images(current_series_images)
                series_list.append(series)
            
            # Neue Serie starten
            current_series_images = [curr_img]
        else:
            # Zur aktuellen Serie hinzufügen
            current_series_images.append(curr_img)
    
    # Letzte Serie abschliessen
    if len(current_series_images) >= min_series_size:
        series = create_series_from_images(current_series_images)
        series_list.append(series)
    
    return series_list


def create_series_from_images(images: List[Dict[str, Any]]) -> Series:
    """
    Erstellt Series-Objekt aus Liste von Bildern.
    
    Args:
        images: Liste von Bild-Entrys
    
    Returns:
        Series-Objekt
    """
    def get_datetime(img: Dict[str, Any]) -> datetime:
        dt_str = img.get("datetime_original", "")
        if dt_str:
            try:
                return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass
        return datetime.min
    
    datetimes = [get_datetime(img) for img in images]
    start_time = min(datetimes)
    end_time = max(datetimes)
    
    # Series-ID generieren
    series_id = generate_series_id(images[0], start_time)
    
    return Series(
        series_id=series_id,
        images=images,
        start_time=start_time,
        end_time=end_time,
        metadata={
            "detection_method": "time_gap",
            "num_images": len(images),
        }
    )


def generate_series_id(first_image: Dict[str, Any], start_time: datetime) -> str:
    """
    Generiert eindeutige Series-ID.
    
    Args:
        first_image: Erstes Bild in Serie
        start_time: Startzeit der Serie
    
    Returns:
        Series-ID (z.B. "20260809-120000-series-001")
    """
    date_str = start_time.strftime("%Y%m%d-%H%M%S")
    
    # Hash für Eindeutigkeit
    rel_path = first_image.get("rel_path", "")
    hash_input = f"{date_str}|{rel_path}"
    hash_hex = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:4]
    
    return f"{date_str}-series-{hash_hex}"


# =============================================================================
# Visuelle Aehnlichkeit (CLIP-basiert)
# =============================================================================

def cluster_by_similarity(images: List[Dict[str, Any]], 
                          embeddings: List[List[float]],
                          similarity_threshold: float = 0.85) -> List[List[Dict[str, Any]]]:
    """
    Clustert Bilder nach visueller Aehnlichkeit (Embeddings).
    
    Args:
        images: Liste von Bild-Entrys
        embeddings: Liste von Embeddings (gleiche Laenge wie images)
        similarity_threshold: Aehnlichkeits-Schwelle (default: 0.85)
    
    Returns:
        Liste von Clustern (jeweils Liste von Bildern)
    """
    if not images or not embeddings:
        return []
    
    # Einfaches Clustering: Greedy
    clusters: List[List[Dict[str, Any]]] = []
    assigned = set()
    
    for i, img in enumerate(images):
        if i in assigned:
            continue
        
        # Neuen Cluster starten
        cluster = [img]
        assigned.add(i)
        
        # Aehnliche Bilder finden
        for j in range(i + 1, len(images)):
            if j in assigned:
                continue
            
            similarity = cosine_similarity(embeddings[i], embeddings[j])
            
            if similarity >= similarity_threshold:
                cluster.append(images[j])
                assigned.add(j)
        
        clusters.append(cluster)
    
    return clusters


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """
    Berechnet Cosine-Similarity zwischen zwei Vektoren.
    
    Args:
        a: Vektor a
        b: Vektor b
    
    Returns:
        Similarity (0-1)
    """
    import math
    
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return dot_product / (norm_a * norm_b)


# =============================================================================
# Hilfsfunktionen
# =============================================================================

def get_single_images(images: List[Dict[str, Any]], 
                      series: List[Series]) -> List[Dict[str, Any]]:
    """
    Gibt Einzelbilder zurueck (nicht in Serien).
    
    Args:
        images: Alle Bilder
        series: Erkannte Serien
    
    Returns:
        Liste von Einzelbildern
    """
    # Alle Bilder in Serien
    series_paths = set()
    for series in series:
        for img in series.images:
            series_paths.add(img.get("rel_path"))
    
    # Einzelbilder
    single_images = [img for img in images if img.get("rel_path") not in series_paths]
    
    return single_images