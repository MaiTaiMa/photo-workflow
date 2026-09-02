import json
import subprocess
from pathlib import Path

from PIL import Image

from app.family_recognition import write_native_tags


def _image(path: Path) -> None:
    Image.new("RGB", (400, 300), (200, 120, 60)).save(path, "JPEG", quality=90)


def _read_regions(path: Path) -> list[dict]:
    result = subprocess.run(
        ["exiftool", "-j", "-struct", "-XMP-mwg-rs:RegionInfo", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    region_info = json.loads(result.stdout)[0].get("RegionInfo", {})
    return region_info.get("RegionList", []) if isinstance(region_info, dict) else []


def _cfg(enabled: bool, persons: list[dict] | None = None) -> dict:
    return {
        "family_recognition": {
            "write_face_regions": enabled,
            "persons": persons or [],
        },
    }


def _peter_region() -> list[dict]:
    return [{
        "name": "peter",
        "left": 100,
        "top": 50,
        "right": 200,
        "bottom": 150,
    }]


def test_face_regions_disabled_writes_only_tags(tmp_path: Path) -> None:
    image = tmp_path / "disabled.jpg"
    _image(image)

    ok, status = write_native_tags(
        image,
        ["person:peter"],
        _cfg(False),
        _peter_region(),
    )

    assert (ok, status) == (True, "ok")
    assert _read_regions(image) == []


def test_face_regions_enabled_uses_display_name_and_mwg_coordinates(
    tmp_path: Path,
) -> None:
    image = tmp_path / "enabled.jpg"
    _image(image)

    ok, status = write_native_tags(
        image,
        ["person:peter"],
        _cfg(True, [{"name": "Peter", "id": "peter"}]),
        _peter_region(),
    )

    assert (ok, status) == (True, "ok")
    written = _read_regions(image)
    assert len(written) == 1
    assert written[0]["Name"] == "Peter"
    assert written[0]["Type"] == "Face"
    assert written[0]["Area"]["Unit"] == "normalized"
    assert written[0]["Area"]["X"] == 0.375
    assert written[0]["Area"]["Y"] == 0.333333
    assert written[0]["Area"]["W"] == 0.25
    assert written[0]["Area"]["H"] == 0.333333


def test_missing_display_mapping_uses_id_as_fallback(tmp_path: Path) -> None:
    image = tmp_path / "fallback.jpg"
    _image(image)

    ok, status = write_native_tags(
        image,
        ["person:peter"],
        _cfg(True),
        _peter_region(),
    )

    assert (ok, status) == (True, "ok")
    assert _read_regions(image)[0]["Name"] == "peter"


def test_identical_regions_are_idempotent(tmp_path: Path) -> None:
    image = tmp_path / "idempotent.jpg"
    _image(image)
    cfg = _cfg(True, [{"name": "Peter", "id": "peter"}])

    first = write_native_tags(image, ["person:peter"], cfg, _peter_region())
    second = write_native_tags(image, ["person:peter"], cfg, _peter_region())

    assert first == (True, "ok")
    assert second == (True, "ok")
    assert len(_read_regions(image)) == 1


def test_invalid_face_box_has_no_metadata_side_effect(tmp_path: Path) -> None:
    image = tmp_path / "invalid.jpg"
    _image(image)
    invalid = [{
        "name": "peter",
        "left": 200,
        "top": 50,
        "right": 100,
        "bottom": 150,
    }]

    ok, status = write_native_tags(
        image,
        ["person:peter"],
        _cfg(True),
        invalid,
    )

    assert (ok, status) == (False, "regions_invalid_box")
    assert _read_regions(image) == []
