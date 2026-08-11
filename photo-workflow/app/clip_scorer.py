"""
# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/clip_scorer.py
# PURPOSE:     CLIP-Score-Berechnung (AP6)
# AUTHOR:      Benjamin (via AP6-Implementierung)
# DATE:        2026-08-09
# VERSION:     1.1.0 (AP6B)
# REQUIRES:    Python 3.8+, transformers, torch, Pillow
# CHANGES:
#   2026-08-12: AP6B – None statt 0.5-Fallback; optionaler Referenz-Cache
# =============================================================================
"""

import os
from typing import Dict, List, Any, Tuple, Optional, Union
from pathlib import Path

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


class CLIPScorer:
    """
    CLIP-Score-Berechnung für Bilder mit optionalem Referenz-Cache.
    """

    def __init__(self, model_path: str, local_files_only: bool = True,
                 shadow_mode: bool = True):
        self.model_path = model_path
        self.local_files_only = local_files_only
        self.shadow_mode = shadow_mode

        self.model = None
        self.processor = None
        self.device = "cpu"

        if not shadow_mode:
            self._load_model()

    def _load_model(self) -> None:
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers, torch, Pillow nicht installiert")

        if not os.path.isdir(self.model_path):
            raise FileNotFoundError(f"Modell-Pfad nicht gefunden: {self.model_path}")

        self.model = CLIPModel.from_pretrained(
            self.model_path,
            local_files_only=self.local_files_only
        )
        self.processor = CLIPProcessor.from_pretrained(
            self.model_path,
            local_files_only=self.local_files_only
        )

        if torch and torch.cuda.is_available():
            self.device = "cuda"
        self.model.to(self.device)
        self.model.eval()

    def compute_clip_score(self, image_path: str, reference_images: List[str],
                           text_prompts: Optional[List[str]] = None) -> Optional[float]:
        if self.shadow_mode:
            return None

        if not TRANSFORMERS_AVAILABLE:
            return None

        try:
            image = Image.open(image_path).convert("RGB")

            ref_images = []
            for ref_path in reference_images:
                try:
                    ref_img = Image.open(ref_path).convert("RGB")
                    ref_images.append(ref_img)
                except (IOError, OSError):
                    continue

            if not ref_images:
                return None

            inputs = self.processor(
                images=[image] + ref_images,
                return_tensors="pt",
                padding=True
            )

            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)

            image_embedding = image_features[0:1]
            ref_embeddings = image_features[1:]

            image_embedding = image_embedding / image_embedding.norm(dim=-1, keepdim=True)
            ref_embeddings = ref_embeddings / ref_embeddings.norm(dim=-1, keepdim=True)

            similarity = (image_embedding @ ref_embeddings.T).squeeze()

            if similarity.dim() == 0:
                score = similarity.item()
            else:
                score = similarity.max().item()

            score = (score + 1) / 2
            return min(1.0, max(0.0, score))

        except Exception:
            return None

    def compute_personal_score(self, image_path: str,
                               personal_references: List[str],
                               reference_dir: Optional[str] = None,
                               cache_path: Optional[str] = None,
                               model_id: Optional[str] = None) -> Optional[float]:
        return self.compute_clip_score(image_path, personal_references)

    def compute_aesthetic_score(self, image_path: str, aesthetic_references: List[str]) -> Optional[float]:
        return self.compute_clip_score(image_path, aesthetic_references)


def compute_clip_score(image_path: str, model_path: str,
                       reference_images: List[str],
                       local_files_only: bool = True,
                       shadow_mode: bool = True) -> Optional[float]:
    scorer = CLIPScorer(model_path, local_files_only, shadow_mode)
    return scorer.compute_clip_score(image_path, reference_images)


def compute_batch_scores(image_paths: List[str], model_path: str,
                         reference_images: List[str],
                         local_files_only: bool = True,
                         shadow_mode: bool = True,
                         batch_size: int = 8) -> List[Tuple[str, Optional[float]]]:
    scorer = CLIPScorer(model_path, local_files_only, shadow_mode)
    results = []
    for image_path in image_paths:
        score = scorer.compute_clip_score(image_path, reference_images)
        results.append((image_path, score))
    return results
