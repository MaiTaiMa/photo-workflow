"""
Skript: app/auto_decision.py
Zweck: Trifft automatische Keep/Reject-Entscheidungen
Version: 1.0.0
"""

import json
from pathlib import Path
from typing import Dict, Any

class AutoDecider:
    """Trifft automatische Review-Entscheidungen basierend auf Config."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def should_auto_decide(self, image_scores: Dict[str, float]) -> bool:
        """
        Prüft ob automatische Entscheidung möglich ist.
        
        Returns:
            True wenn auto_mode aktiv und confidence_threshold erreicht
        """
        if not self.config.get('automation', {}).get('auto_mode', False):
            return False
        
        return True
    
    def decide(self, image_scores: Dict[str, float]) -> str:
        """
        Trifft automatische Entscheidung für ein Bild.
        
        Args:
            image_scores: {
                'personal_score': 0.87,
                'base_score': 0.75,
                'eye_score': 0.82
            }
        
        Returns:
            'auto_keep', 'auto_reject', oder 'manual_review'
        """
        if not self.should_auto_decide(image_scores):
            return 'manual_review'
        
        threshold = self.config['automation']['confidence_threshold']
        personal_score = image_scores.get('personal_score', 0.0)
        
        if personal_score >= threshold:
            return 'auto_keep'
        else:
            return 'auto_reject'
    
    def get_decision_reason(self, decision: str, image_scores: Dict[str, float]) -> str:
        """Erklärt die Entscheidungsfindung."""
        if decision == 'auto_keep':
            return f"auto_keep_high_score:personal_score={image_scores.get('personal_score', 0.0):.2f}"
        elif decision == 'auto_reject':
            return f"auto_reject_low_score:personal_score={image_scores.get('personal_score', 0.0):.2f}"
        else:
            return "manual_review_required:auto_mode_disabled"

    def predict_decision(
        *,
        personal_score: float | None,
        final_score: float | None,
        config: dict[str, Any],
    ) -> tuple[str, str]:
        """Erstellt eine KI-Prognose, ohne den finalen Review-State zu verändern."""
        automation = config["automation"]

        if automation["mode"] == "off":
            return "review", "automation_off"

        if personal_score is None or final_score is None:
            return "review", "score_unavailable"

        keep_min = float(automation["keep_score_min"])
        reject_max = float(automation["reject_score_max"])

        if personal_score >= keep_min and final_score >= keep_min:
            return "keep", "high_confidence_keep"

        if personal_score <= reject_max and final_score <= reject_max:
            return "reject", "high_confidence_reject"

        return "review", "manual_review_zone"