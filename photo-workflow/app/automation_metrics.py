# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/automation_metrics.py
# PURPOSE:     Berechnet Metriken für Vollautomatik-Readiness
# AUTHOR:      Matzethias
# DATE:        2026-08-29
# VERSION:     1.0.0
# REQUIRES:    Python 3.11+
# CHANGES:
#   Initial version
# =============================================================================


import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

class AutomationMetrics:
    """Berechnet Readiness-Metriken für Vollautomatik."""
    
    def __init__(self, runtime_path: Path):
        self.runtime_path = runtime_path
        self.validation_path = runtime_path / "validation"
    
    def load_all_validations(self) -> List[Dict]:
        """Lädt alle Validation-Reports."""
        if not self.validation_path.exists():
            return []
        
        reports = []
        for file in self.validation_path.glob("validation_*.json"):
            with open(file, 'r') as f:
                reports.append(json.load(f))
        
        return reports
    
    def calculate_readiness(self, min_batches: int = 10, threshold: float = 0.85) -> Dict[str, Any]:
        """
        Berechnet ob Vollautomatik aktiviert werden kann.
        
        Args:
            min_batches: Mindestanzahl Batches für statistische Signifikanz
            threshold: Mindest-Übereinstimmungsrate (85%)
        
        Returns:
            {
                "total_batches": 15,
                "avg_agreement_rate": 0.89,
                "batches_above_threshold": 12,
                "ready_for_auto_mode": True,
                "calculated_at": "2026-08-10T00:00:00Z"
            }
        """
        reports = self.load_all_validations()
        
        if not reports:
            return {
                "total_batches": 0,
                "avg_agreement_rate": 0.0,
                "batches_above_threshold": 0,
                "ready_for_auto_mode": False,
                "calculated_at": datetime.now().isoformat(),
                "error": "no_validation_data"
            }
        
        # Filtere Reports mit Daten
        valid_reports = [r for r in reports if r.get('total_decisions', 0) > 0]
        
        if len(valid_reports) < min_batches:
            return {
                "total_batches": len(valid_reports),
                "avg_agreement_rate": 0.0,
                "batches_above_threshold": 0,
                "ready_for_auto_mode": False,
                "calculated_at": datetime.now().isoformat(),
                "error": f"insufficient_batches: {len(valid_reports)} < {min_batches}"
            }
        
        # Berechne Metriken
        agreement_rates = [r['agreement_rate'] for r in valid_reports]
        avg_agreement = sum(agreement_rates) / len(agreement_rates)
        batches_above = sum(1 for r in valid_reports if r['agreement_rate'] >= threshold)
        
        ready = (len(valid_reports) >= min_batches and 
                 avg_agreement >= threshold and 
                 batches_above >= min_batches)
        
        return {
            "total_batches": len(valid_reports),
            "avg_agreement_rate": round(avg_agreement, 4),
            "batches_above_threshold": batches_above,
            "ready_for_auto_mode": ready,
            "calculated_at": datetime.now().isoformat()
        }
    
    def save_metrics(self, metrics: Dict, output_path: Path):
        """Speichert Automation-Metrics."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        temp_path = output_path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        temp_path.rename(output_path)