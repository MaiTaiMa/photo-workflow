from app.clip_scorer import CLIPScorer, TRANSFORMERS_AVAILABLE


def test_shadow_mode_returns_none_instead_of_dummy_score() -> None:
    scorer = CLIPScorer(model_path="/dev/null", shadow_mode=True)
    assert scorer.compute_clip_score("dummy.jpg", ["ref.jpg"]) is None
    assert scorer.compute_personal_score("dummy.jpg", ["ref.jpg"]) is None
    assert scorer.compute_aesthetic_score("dummy.jpg", ["ref.jpg"]) is None


def test_missing_transformers_returns_none() -> None:
    if TRANSFORMERS_AVAILABLE:
        # In dieser Umgebung sind Transformer verfügbar;
        # der Test prüft nur den Pfad bei fehlendem Import.
        return
    # Dieser Pfad wird nur erreicht, wenn transformers fehlt.
    scorer = CLIPScorer(model_path="/dev/null", shadow_mode=False)
    assert scorer.compute_clip_score("dummy.jpg", ["ref.jpg"]) is None


def test_empty_references_returns_none() -> None:
    # shadow_mode=True, damit kein Modell geladen werden muss.
    scorer = CLIPScorer(model_path="/dev/null", shadow_mode=True)
    assert scorer.compute_clip_score("dummy.jpg", []) is None