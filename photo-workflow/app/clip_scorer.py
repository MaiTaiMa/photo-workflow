"""
# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/clip_scorer.py
# PURPOSE:     CLIP-Score-Berechnung (AP6)
# AUTHOR:      Benjamin (via AP6-Implementierung)
# DATE:        2026-08-09
# VERSION:     1.0.0 (AP6)
# REQUIRES:    Python 3.8+, transformers, torch, Pillow
# CHANGES:
#   2026-08-09: Initiale Implementierung für AP6
#               - CLIPScorer-Klasse für Score-Berechnung
#               - compute_clip_score() für Einzelbild-Score
#               - compute_batch_scores() für Batch-Verarbeitung
#               - Shadow-Mode für Dry-Run
# =============================================================================
"""

import os
from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
#from app.auto_decision import AutoDecider

# Transformer-Imports (optional, nur wenn verfügbar)
try:
    from transformers import CLIPModel, CLIPProcessor
    import torch
    from PIL import Image
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    CLIPModel = None
    CLIPProcessor = None
    torch = None
    Image = None


# =============================================================================
# CLIPScorer-Klasse
# =============================================================================

class CLIPScorer:
    """
    CLIP-Score-Berechnung für Bilder.
    """
    
    def __init__(self, model_path: str, local_files_only: bool = True,
                 shadow_mode: bool = True):
        """
        Initialisiert CLIP-Scorer.
        
        Args:
            model_path: Pfad zum lokalen CLIP-Modell
            local_files_only: Keine Downloads (True für Produktion)
            shadow_mode: Nur Logging, keine Mutationen (True für Testing)
        """
        self.model_path = model_path
        self.local_files_only = local_files_only
        self.shadow_mode = shadow_mode
        
        self.model = None
        self.processor = None
        self.device = "cpu"
        
        # Initialisierung verzoe gert (lazy loading)
        if not shadow_mode:
            self._load_model()
    
    def _load_model(self) -> None:
        """Laedt CLIP-Modell (lazy)."""
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers, torch, Pillow nicht installiert")
        
        if not os.path.isdir(self.model_path):
            raise FileNotFoundError(f"Modell-Pfad nicht gefunden: {self.model_path}")
        
        # Modell laden (lokal, kein Download)
        self.model = CLIPModel.from_pretrained(
            self.model_path,
            local_files_only=self.local_files_only
        )
        
        self.processor = CLIPProcessor.from_pretrained(
            self.model_path,
            local_files_only=self.local_files_only
        )
        
        # Device
        if torch and torch.cuda.is_available():
            self.device = "cuda"
        self.model.to(self.device)
        self.model.eval()
    
    def compute_clip_score(self, image_path: str, reference_images: List[str],
                           text_prompts: Optional[List[str]] = None) -> float:
        """
        Berechnet CLIP-Score für ein Bild.
        
        Args:
            image_path: Pfad zum Bild
            reference_images: Liste von Referenzbildern (Pfade)
            text_prompts: Optionale Text-Prompts
        
        Returns:
            CLIP-Score (0-1)
        """
        if self.shadow_mode:
            # Shadow-Mode: nur Dummy-Score
            return 0.5
        
        if not TRANSFORMERS_AVAILABLE:
            return 0.5
        
        try:
            # Bild laden
            image = Image.open(image_path).convert("RGB")
            
            # Referenzbilder laden
            ref_images = []
            for ref_path in reference_images:
                try:
                    ref_img = Image.open(ref_path).convert("RGB")
                    ref_images.append(ref_img)
                except (IOError, OSError):
                    continue
            
            if not ref_images:
                return 0.5  # Keine Referenzen
            
            # Processor
            inputs = self.processor(
                images=[image] + ref_images,
                return_tensors="pt",
                padding=True
            )
            
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Embeddings
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
            
            # Aehnlichkeit berechnen (Cosine Similarity)
            image_embedding = image_features[0:1]  # Query-Bild
            ref_embeddings = image_features[1:]     # Referenzen
            
            # Normalisieren
            image_embedding = image_embedding / image_embedding.norm(dim=-1, keepdim=True)
            ref_embeddings = ref_embeddings / ref_embeddings.norm(dim=-1, keepdim=True)
            
            # Aehnlichkeit
            similarity = (image_embedding @ ref_embeddings.T).squeeze()
            
            # Maximum (beste Aehnlichkeit)
            if similarity.dim() == 0:
                score = similarity.item()
            else:
                score = similarity.max().item()
            
            # Auf 0-1 normalisieren (CLIP liefert -1 bis 1)
            score = (score + 1) / 2
            
            return min(1.0, max(0.0, score))
        
        except Exception as e:
            # Fehler: 0.5 als Fallback
            return 0.5
    
    def compute_personal_score(self, image_path: str, personal_references: List[str]) -> float:
        """
        Berechnet personal_score (CLIP-basiert).
        
        Args:
            image_path: Pfad zum Bild
            personal_references: Liste von personal_training Referenzen
        
        Returns:
            personal_score (0-1)
        """
        return self.compute_clip_score(image_path, personal_references)
    
    def compute_aesthetic_score(self, image_path: str, aesthetic_references: List[str]) -> float:
        """
        Berechnet aesthetic_reference_score (CLIP-basiert).
        
        Args:
            image_path: Pfad zum Bild
            aesthetic_references: Liste von aesthetic_reference Referenzen
        
        Returns:
            aesthetic_reference_score (0-1)
        """
        return self.compute_clip_score(image_path, aesthetic_references)


# =============================================================================
# Hilfsfunktionen
# =============================================================================

def compute_clip_score(image_path: str, model_path: str, 
                       reference_images: List[str],
                       local_files_only: bool = True,
                       shadow_mode: bool = True) -> float:
    """
    Berechnet CLIP-Score (Hilfsfunktion).
    
    Args:
        image_path: Pfad zum Bild
        model_path: Pfad zum CLIP-Modell
        reference_images: Referenzbilder
        local_files_only: Keine Downloads
        shadow_mode: Shadow-Mode
    
    Returns:
        CLIP-Score (0-1)
    """
    scorer = CLIPScorer(model_path, local_files_only, shadow_mode)
    return scorer.compute_clip_score(image_path, reference_images)


def compute_batch_scores(image_paths: List[str], model_path: str,
                         reference_images: List[str],
                         local_files_only: bool = True,
                         shadow_mode: bool = True,
                         batch_size: int = 8) -> List[Tuple[str, float]]:
    """
    Berechnet CLIP-Scores für Batch von Bildern.
    
    Args:
        image_paths: Liste von Bildpfaden
        model_path: Pfad zum CLIP-Modell
        reference_images: Referenzbilder
        local_files_only: Keine Downloads
        shadow_mode: Shadow-Mode
        batch_size: Batch-Groesse
    
    Returns:
        Liste von (image_path, score) Tupeln
    """
    scorer = CLIPScorer(model_path, local_files_only, shadow_mode)
    
    results = []
    for image_path in image_paths:
        score = scorer.compute_clip_score(image_path, reference_images)
        results.append((image_path, score))
    
    return results