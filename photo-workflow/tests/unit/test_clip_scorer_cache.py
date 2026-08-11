from app.clip_scorer import CLIPScorer


def test_shadow_mode_returns_none_instead_of_dummy_score() -> None:
    scorer = CLIPScorer(model_path="/dev/null", shadow_mode=True)
    assert scorer.compute_clip_score("dummy.jpg", ["ref.jpg"]) is None
    assert scorer.compute_personal_score("dummy.jpg", ["ref.jpg"]) is None
    assert scorer.compute_aesthetic_score("dummy.jpg", ["ref.jpg"]) is None


def test_missing_transformers_returns_none() -> None:
    if CLIPScorer.__module__ is None:
        return
    scorer = CLIPScorer(model_path="/dev/null", shadow_mode=False)
    assert scorer.compute_clip_score("dummy.jpg", ["ref.jpg"]) is None


def test_empty_references_returns_none() -> None:
    scorer = CLIPScorer(model_path="/dev/null", shadow_mode=False)
    assert scorer.compute_clip_score("dummy.jpg", []) is None
