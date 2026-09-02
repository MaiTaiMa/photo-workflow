# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/auto_decision.py
# PURPOSE:     Erstellt nicht-operative KI-Prognosen für den Review-Workflow.
# AUTHOR:      Matzethias
# DATE:        2026-08-20
# VERSION:     1.2.1
# REQUIRES:    Python 3.11, typing
# CHANGES:
#   2026-08-26 | 1.2.1 | Header und Kommentierung gemäß Implementierungsregeln ergänzt.
#   2026-08-20 | 1.2.0 | A1: Vertragskonforme, nicht-operative Automationsmodi.
# =============================================================================


from typing import Any, Mapping


# -----------------------------------------------------------------------------
# Vertragswerte für die rein diagnostische Prediction-Konfiguration.
# Ungültige Werte werden bewusst nicht normalisiert, sondern fail-closed abgelehnt.
# -----------------------------------------------------------------------------
VALID_AUTOMATION_MODES = frozenset({
    "off",
    "shadow",
    "assisted",
    "auto_phase1",
    "auto_phase2",
    "full_auto",
})


# -----------------------------------------------------------------------------
# Prediction aus validierten Scores ableiten, ohne finale Reviewdaten zu ändern.
# Die Rückgabe ist ausschließlich ein persistierbarer diagnostischer Vorschlag.
# -----------------------------------------------------------------------------
def predict_decision(
    *,
    personal_score: float | None,
    final_score: float | None,
    config: Mapping[str, Any],
) -> tuple[str, str]:
    """Erstellt eine nicht-operative Keep-, Reject- oder Review-Prognose.

    Eingabe: Persönlicher Score, finaler Score und Automation-Konfiguration.
    Ausgabe: Vorschlag plus begründender, secrets-freier Auditgrund.
    Sicherheit: Fehlende oder ungültige Werte führen zu review oder ValueError.
    """
    automation = config.get("automation")
    if not isinstance(automation, Mapping):
        raise ValueError("automation configuration is required")

    mode = automation.get("mode", "off")
    if mode not in VALID_AUTOMATION_MODES:
        raise ValueError(f"unsupported automation mode: {mode}")
    # -------------------------------------------------------------------------
    # Der deaktivierte Modus darf nie eine operative Vorhersage ermöglichen.
    # Rückgabe review hält die nachgelagerte menschliche Entscheidung zwingend offen.
    # -------------------------------------------------------------------------
    if mode == "off":
        return "review", "automation_off"

    # -------------------------------------------------------------------------
    # shadow: Nur lernen, keine Automation
    # -------------------------------------------------------------------------
    if mode == "shadow":
        return "review", "shadow_mode_learning_only"

    # -------------------------------------------------------------------------
    # assisted: Vorschlaege bei hoher Sicherheit, sonst review
    # -------------------------------------------------------------------------
    if mode == "assisted":
        # assisted braucht hoehere Scores als full_auto (konservativer)
        keep_min = float(automation["keep_score_min"])
        reject_max = float(automation["reject_score_max"])
        # assisted: +0.10 auf beide Schwellen
        assisted_keep_min = min(keep_min + 0.10, 1.0)
        assisted_reject_max = max(reject_max - 0.10, 0.0)

        if personal_score >= assisted_keep_min and final_score >= assisted_keep_min:
            return "keep", "assisted_confident_keep"
        if personal_score <= assisted_reject_max and final_score <= assisted_reject_max:
            return "reject", "assisted_confident_reject"
        return "review", "assisted_uncertain"


    if personal_score is None or final_score is None:
        return "review", "score_unavailable"

    # -------------------------------------------------------------------------
    # Beide Scores müssen dieselbe sichere Schwellenlogik erfüllen.
    # Uneindeutige Werte verbleiben bewusst in der manuellen Review-Zone.
    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # Beide Scores müssen dieselbe sichere Schwellenlogik erfüllen.
    # Uneindeutige Werte verbleiben bewusst in der manuellen Review-Zone.
    # -------------------------------------------------------------------------
    keep_min = float(automation["keep_score_min"])
    reject_max = float(automation["reject_score_max"])
    if not 0.0 <= reject_max < keep_min <= 1.0:
        raise ValueError("automation thresholds must satisfy 0 <= reject < keep <= 1")

    if personal_score >= keep_min and final_score >= keep_min:
        return "keep", "high_confidence_keep"
    if personal_score <= reject_max and final_score <= reject_max:
        return "reject", "high_confidence_reject"
    return "review", "manual_review_zone"


# -----------------------------------------------------------------------------
# Kompatibilitätsschicht für bestehende Aufrufer ohne eigene Entscheidungswirkung.
# Sie delegiert unverändert an die zentrale, rein diagnostische Prediction-Funktion.
# -----------------------------------------------------------------------------
class AutoDecider:
    """Kapselt die nicht-operative Prediction für bestehende Aufrufer.

    Eingabe: Eine zuvor bereitgestellte Automation-Konfiguration.
    Ausgabe: Dieselbe Prognose wie predict_decision().
    Sicherheit: Die Klasse führt keine Datei- oder Statusänderung aus.
    """

    def __init__(self, config: Mapping[str, Any]):
        self.config = config

    def predict_decision(
        self,
        *,
        personal_score: float | None,
        final_score: float | None,
    ) -> tuple[str, str]:
        """Delegiert die Prediction ohne Änderung einer finalen Reviewentscheidung.

        Eingabe: Persönlicher Score und finaler Score des aktuellen Bildes.
        Ausgabe: Nicht-operative Prognose mit nachvollziehbarem Grund.
        Sicherheit: Es werden keine Dateien, States oder Handoffs verändert.
        """
        return predict_decision(
            personal_score=personal_score,
            final_score=final_score,
            config=self.config,
        )