"""Tests fuer _load_person_weights (casefold + persons[].weight Vorrang)."""

from app.family_recognition import _load_person_weights


def test_casefold_greift_fuer_grossgeschriebene_schluessel():
    cfg = {"person_weights": {"Finn": 0.55, "Lilly": 0.55}}
    weights = _load_person_weights(cfg)
    assert weights["finn"] == 0.55
    assert weights["lilly"] == 0.55


def test_persons_weight_hat_vorrang():
    cfg = {
        "person_weights": {"finn": 0.4},
        "persons": [{"id": "finn", "name": "Finn", "weight": 0.6}],
    }
    assert _load_person_weights(cfg)["finn"] == 0.6


def test_leere_config_liefert_leeres_dict():
    assert _load_person_weights({}) == {}
    assert _load_person_weights({"person_weights": None}) == {}
    assert _load_person_weights({"persons": [{"id": "x", "weight": "kaputt"}]}) == {}


def test_persons_only_nach_migration():
    cfg = {"persons": [
        {"id": "nelly", "name": "Nelly (Mama)", "weight": 0.35},
        {"id": "finn", "name": "Finn", "weight": 0.55},
        {"id": "peter", "name": "Peter"},
    ]}
    assert _load_person_weights(cfg) == {"nelly": 0.35, "finn": 0.55}
