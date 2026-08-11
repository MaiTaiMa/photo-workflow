from pathlib import Path

from app.personal_score_cache import load_or_build_reference_cache, reference_fingerprint


def _write_reference(directory: Path, name: str, content: bytes) -> Path:
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def test_reference_fingerprint_is_stable_and_changes_with_content(tmp_path) -> None:
    references = tmp_path / "references"
    image = _write_reference(references, "a.jpg", b"first")

    first, paths = reference_fingerprint(references)
    second, _ = reference_fingerprint(references)
    image.write_bytes(b"changed")
    changed, _ = reference_fingerprint(references)

    assert paths == [image]
    assert first == second
    assert changed != first


def test_matching_reference_and_model_reuse_cache(tmp_path) -> None:
    references = tmp_path / "references"
    _write_reference(references, "a.jpg", b"one")
    calls: list[Path] = []

    def embed(path: Path) -> list[float]:
        calls.append(path)
        return [0.1, 0.2]

    kwargs = {
        "reference_dir": references,
        "cache_path": tmp_path / "runtime" / "personal-score-cache.json",
        "model_id": "clip-vit-test",
        "embed": embed,
    }
    first, first_from_cache = load_or_build_reference_cache(**kwargs)
    second, second_from_cache = load_or_build_reference_cache(**kwargs)

    assert first == second == {"a.jpg": [0.1, 0.2]}
    assert first_from_cache is False
    assert second_from_cache is True
    assert len(calls) == 1


def test_reference_or_model_change_invalidates_cache(tmp_path) -> None:
    references = tmp_path / "references"
    image = _write_reference(references, "a.jpg", b"one")
    calls: list[Path] = []

    def embed(path: Path) -> list[float]:
        calls.append(path)
        return [float(len(calls))]

    cache_path = tmp_path / "runtime" / "personal-score-cache.json"
    load_or_build_reference_cache(
        reference_dir=references,
        cache_path=cache_path,
        model_id="clip-v1",
        embed=embed,
    )
    image.write_bytes(b"two")
    _, content_changed_from_cache = load_or_build_reference_cache(
        reference_dir=references,
        cache_path=cache_path,
        model_id="clip-v1",
        embed=embed,
    )
    _, model_changed_from_cache = load_or_build_reference_cache(
        reference_dir=references,
        cache_path=cache_path,
        model_id="clip-v2",
        embed=embed,
    )

    assert content_changed_from_cache is False
    assert model_changed_from_cache is False
    assert len(calls) == 3
