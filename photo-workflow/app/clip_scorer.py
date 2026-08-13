"""
Skript: app/clip_scorer.py
Zweck: Lokales CLIP-Scoring mit sicherem Referenz-Embedding-Cache.
Version: 1.2.0
"""

import os
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from app.personal_score_cache import load_or_build_reference_cache

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
    """Compute local CLIP similarity scores without network downloads."""

    def __init__(self, model_path: str, local_files_only: bool = True,
                 shadow_mode: bool = True):
        self.model_path = model_path
        self.local_files_only = local_files_only
        self.shadow_mode = shadow_mode
        self.model = None
        self.processor = None
        self.device = "cpu"
        self.last_personal_cache_status = "not_requested"
        if not shadow_mode:
            self._load_model()

    def _load_model(self) -> None:
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers, torch, Pillow nicht installiert")
        if not os.path.isdir(self.model_path):
            raise FileNotFoundError(f"Modell-Pfad nicht gefunden: {self.model_path}")
        self.model = CLIPModel.from_pretrained(
            self.model_path, local_files_only=self.local_files_only
        )
        self.processor = CLIPProcessor.from_pretrained(
            self.model_path, local_files_only=self.local_files_only
        )
        if torch and torch.cuda.is_available():
            self.device = "cuda"
        self.model.to(self.device)
        self.model.eval()

    def _embed_image(self, image_path: Path) -> list[float]:
        """Create one L2-normalized CLIP image embedding as plain numbers."""
        if self.shadow_mode or not TRANSFORMERS_AVAILABLE:
            raise RuntimeError("CLIP embedding is unavailable")
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=[image], return_tensors="pt")
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with torch.no_grad():
            features = self.model.get_image_features(**inputs)[0]
        norm = features.norm()
        if not torch.isfinite(norm) or norm.item() == 0:
            raise ValueError("CLIP returned an invalid embedding")
        return (features / norm).detach().cpu().tolist()

    @staticmethod
    def _score(query: list[float], references: list[list[float]]) -> Optional[float]:
        if not query or not references or any(len(vector) != len(query) for vector in references):
            return None
        query_norm = sum(value * value for value in query) ** 0.5
        if query_norm == 0:
            return None
        similarities = []
        for vector in references:
            vector_norm = sum(value * value for value in vector) ** 0.5
            if vector_norm == 0:
                continue
            similarities.append(sum(a * b for a, b in zip(query, vector)) / (query_norm * vector_norm))
        if not similarities:
            return None
        return min(1.0, max(0.0, (max(similarities) + 1.0) / 2.0))

    def compute_clip_score(self, image_path: str, reference_images: List[str],
                           text_prompts: Optional[List[str]] = None) -> Optional[float]:
        if self.shadow_mode or not TRANSFORMERS_AVAILABLE or not reference_images:
            return None
        try:
            query = self._embed_image(Path(image_path))
            references = []
            for reference in reference_images:
                try:
                    references.append(self._embed_image(Path(reference)))
                except (OSError, ValueError, RuntimeError):
                    continue
            return self._score(query, references)
        except (OSError, ValueError, RuntimeError):
            return None

    def compute_personal_score(self, image_path: str,
                               personal_references: List[str],
                               reference_dir: Optional[str] = None,
                               cache_path: Optional[str] = None,
                               model_id: Optional[str] = None) -> Optional[float]:
        """Score a query against cached embeddings for one reference directory."""
        self.last_personal_cache_status = "not_used"
        if self.shadow_mode or not TRANSFORMERS_AVAILABLE:
            self.last_personal_cache_status = "unavailable"
            return None
        if not reference_dir or not cache_path:
            return self.compute_clip_score(image_path, personal_references)
        try:
            embeddings, cache_hit = load_or_build_reference_cache(
                reference_dir=reference_dir,
                cache_path=cache_path,
                model_id=model_id or str(Path(self.model_path).resolve()),
                embed=self._embed_image,
            )
            self.last_personal_cache_status = "hit" if cache_hit else "rebuilt"
            query = self._embed_image(Path(image_path))
            return self._score(query, list(embeddings.values()))
        except (OSError, ValueError, RuntimeError):
            self.last_personal_cache_status = "unavailable"
            return None

    def compute_aesthetic_score(self, image_path: str,
                                aesthetic_references: List[str]) -> Optional[float]:
        return self.compute_clip_score(image_path, aesthetic_references)


def compute_clip_score(image_path: str, model_path: str,
                       reference_images: List[str], local_files_only: bool = True,
                       shadow_mode: bool = True) -> Optional[float]:
    return CLIPScorer(model_path, local_files_only, shadow_mode).compute_clip_score(
        image_path, reference_images
    )


def compute_batch_scores(image_paths: List[str], model_path: str,
                         reference_images: List[str], local_files_only: bool = True,
                         shadow_mode: bool = True,
                         batch_size: int =8) -> List[Tuple[str, Optional[float]]]:
    scorer = CLIPScorer(model_path, local_files_only, shadow_mode)
    return [(image_path, scorer.compute_clip_score(image_path, reference_images)) for image_path in image_paths]
