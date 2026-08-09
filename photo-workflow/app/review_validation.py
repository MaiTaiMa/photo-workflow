"""
Skript: app/review_validation.py
Zweck: Validiert manuelle Review-Entscheidungen auf Konsistenz
Version: 1.0.0
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timedelta

class ReviewValidator:
    """Validiert ob Keep/Reject-Entscheidungen später beibehalten wurden."""
    
    def __init__(self, runtime_path: Path):
        self.runtime_path = runtime_path
        self.user_actions_path = runtime_path / "logs" / "user_actions.log"
        self.review_state_path = runtime_path / "state" / "review_state.json"
    
    def load_user_actions(self, batch_id: str, days: int = 30) -> List[Dict]:
        """Lädt User-Actions der letzten N Tage für einen Batch."""
        if not self.user_actions_path.exists():
            return []
        
        actions = []
        cutoff = datetime.now() - timedelta(days=days)
        
        with open(self.user_actions_path, 'r') as f:
            for line in f:
                action = json.loads(line)
                if action.get('batch_id') == batch_id:
                    action_time = datetime.fromisoformat(action['timestamp'])
                    if action_time >= cutoff:
                        actions.append(action)
        
        return actions
    
    def load_review_state(self, batch_id: str) -> Dict:
        """Lädt den Review-State für einen Batch."""
        if not self.review_state_path.exists():
            return {}
        
        with open(self.review_state_path, 'r') as f:
            all_states = json.load(f)
        
        return all_states.get(batch_id, {})
    
    def validate_decisions(self, batch_id: str, window_days: int = 30) -> Dict[str, Any]:
        """
        Validiert Entscheidungen eines Batches.
        
        Returns:
            {
                "batch_id": "batch_001",
                "total_decisions": 100,
                "confirmed_keep": 87,
                "confirmed_reject": 92,
                "agreement_rate": 0.895,
                "validated_at": "2026-08-10T00:00:00Z"
            }
        """
        actions = self.load_user_actions(batch_id, window_days)
        review_state = self.load_review_state(batch_id)
        
        if not actions or not review_state:
            return {
                "batch_id": batch_id,
                "total_decisions": 0,
                "confirmed_keep": 0,
                "confirmed_reject": 0,
                "agreement_rate": 0.0,
                "validated_at": datetime.now().isoformat(),
                "error": "no_data"
            }
        
        # Zähle Entscheidungen
        total = len(actions)
        confirmed_keep = sum(1 for a in actions 
                           if a['action'] == 'keep' and 
                           review_state.get(a['image_id'], {}).get('review_state') == 'manual_keep')
        confirmed_reject = sum(1 for a in actions 
                              if a['action'] == 'reject' and 
                              review_state.get(a['image_id'], {}).get('review_state') == 'manual_reject')
        
        agreement_rate = (confirmed_keep + confirmed_reject) / total if total > 0 else 0.0
        
        return {
            "batch_id": batch_id,
            "total_decisions": total,
            "confirmed_keep": confirmed_keep,
            "confirmed_reject": confirmed_reject,
            "agreement_rate": round(agreement_rate, 4),
            "validated_at": datetime.now().isoformat()
        }
    
    def save_validation_report(self, report: Dict, output_path: Path):
        """Speichert einen Validation-Report."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Atomar schreiben (Spec 02: Atomarität)
        temp_path = output_path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            json.dump(report, f, indent=2)
        temp_path.rename(output_path)