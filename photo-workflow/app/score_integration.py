# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/score_integration.py
# PURPOSE:     Integration von CLIP-Scores mit existing scores (AP6)
# AUTHOR:      Matzethias
# DATE:        2026-08-09
# VERSION:     1.1.0
# REQUIRES:    Python 3.8+, app.clip_scorer
# CHANGES:
#   2026-08-12: AP6B – keine 0.5-Fallbacks; dynamische Regewichtung
# =============================================================================


from typing import Dict, List, Any, Tuple, Optional
from pathlib import Path
import os


def compute_final_score(generic_score: Optional[float] = None,
                        aesthetic_score: Optional[float] = None,
                        personal_score: Optional[float] = None,
                        weights: Optional[Dict[str, float]] = None) -> Optional[float]:
    if weights is None:
        weights = {
            "generic": 0.3,
            "aesthetic": 0.3,
            "personal": 0.4,
        }

    components = []
    active_weights = []

    if generic_score is not None:
        components.append(generic_score)
        active_weights.append(weights["generic"])
    if aesthetic_score is not None:
        components.append(aesthetic_score)
        active_weights.append(weights["aesthetic"])
    if personal_score is not None:
        components.append(personal_score)
        active_weights.append(weights["personal"])

    if not components:
        return None

    total_weight = sum(active_weights)
    if total_weight <= 0:
        return None

    normalized_weights = [w / total_weight for w in active_weights]
    final_score = sum(c * w for c, w in zip(components, normalized_weights))
    return min(1.0, max(0.0, final_score))


def integrate_clip_scores(images: List[Dict[str, Any]],
                          model_path: str,
                          aesthetic_references: List[str],
                          personal_references: List[str],
                          shadow_mode: bool = True,
                          weights: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
    try:
        from app.clip_scorer import CLIPScorer
    except ImportError:
        for image in images:
            image.pop("aesthetic_reference_score", None)
            image.pop("personal_score", None)
            image.pop("final_score", None)
        return images

    scorer = CLIPScorer(model_path, local_files_only=True, shadow_mode=shadow_mode)

    for image in images:
        rel_path = image.get("rel_path", "")
        image_path = rel_path

        aesthetic_score = scorer.compute_aesthetic_score(image_path, aesthetic_references)
        if aesthetic_score is not None:
            image["aesthetic_reference_score"] = aesthetic_score
            image["aesthetic_reference_score_source"] = "clip_aesthetic"
        else:
            image.pop("aesthetic_reference_score", None)
            image.pop("aesthetic_reference_score_source", None)

        personal_score = scorer.compute_personal_score(image_path, personal_references)
        if personal_score is not None:
            image["personal_score"] = personal_score
            image["personal_score_source"] = "clip_personal"
        else:
            image.pop("personal_score", None)
            image.pop("personal_score_source", None)

        generic_score = image.get("score")
        if generic_score is not None:
            image["generic_score"] = generic_score
        else:
            image.pop("generic_score", None)

        final_score = compute_final_score(
            generic_score=generic_score,
            aesthetic_score=aesthetic_score,
            personal_score=personal_score,
            weights=weights,
        )
        if final_score is not None:
            image["final_score"] = final_score
        else:
            image.pop("final_score", None)

    return images


def validate_scores(images: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    warnings = []
    is_valid = True

    for i, image in enumerate(images):
        for score_key in ["generic_score", "aesthetic_reference_score", "personal_score", "final_score"]:
            if score_key in image:
                score = image[score_key]
                if not isinstance(score, (int, float)):
                    warnings.append(f"images[{i}].{score_key} muss eine Zahl sein")
                    is_valid = False
                elif score < 0 or score > 1:
                    warnings.append(f"images[{i}].{score_key} muss zwischen 0 und 1 liegen (ist: {score})")
                    is_valid = False

        for source_key in ["generic_score_source", "aesthetic_reference_score_source", "personal_score_source"]:
            if source_key in image:
                source = image[source_key]
                if not isinstance(source, str):
                    warnings.append(f"images[{i}].{source_key} muss ein String sein")

    return is_valid, warnings


def generate_shadow_report(images: List[Dict[str, Any]],
                           original_images: List[Dict[str, Any]]) -> str:
    lines = []
    lines.append("Shadow-Mode Report: CLIP-Score-Vergleich")
    lines.append("=" * 60)
    lines.append("")

    for i, (image, orig) in enumerate(zip(images[:10], original_images[:10])):
        orig_score = orig.get("score")
        final_score = image.get("final_score")

        if orig_score is None or final_score is None:
            diff_str = "N/A"
        else:
            diff = final_score - orig_score
            diff_str = f"{diff:+.3f}"

        lines.append(f"{i+1}. {image.get('rel_path', 'unknown')}")
        lines.append(f"   Original: {orig_score}")
        lines.append(f"   Mit CLIP: {final_score}")
        lines.append(f"   Diff: {diff_str}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)