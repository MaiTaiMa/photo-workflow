"""Tests fuer die Serienbildung (Zeit, Dateinummer-Fallback, visuell, max_series_size)."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image

from app.series_culling import cluster_series


def _make_image(path: Path, color: str = "white") -> None:
    Image.new("RGB", (16, 16), color).save(path)


def _make_image_with_exif(path: Path, dt: datetime, color: str = "white") -> None:
    img = Image.new("RGB", (16, 16), color)
    exif = Image.Exif()
    exif[36867] = dt.strftime("%Y:%m:%d %H:%M:%S")
    img.save(path, exif=exif)


def test_visual_clustering_unchanged_default(tmp_path: Path) -> None:
    paths = []
    for i, color in enumerate(("white", "white", "black")):
        p = tmp_path / f"IMG_{i:04d}.JPG"
        _make_image(p, color=color)
        paths.append(p)

    labels, _ = cluster_series(paths)
    assert labels[0] == labels[1] != -1
    assert labels[2] == -1


def test_exif_time_groups_close_images(tmp_path: Path) -> None:
    base = datetime(2026, 9, 12, 10, 0, 0)
    paths = []
    dts = []
    for offset in (0, 5, 9, 60):
        p = tmp_path / f"IMG_{offset:04d}.JPG"
        _make_image_with_exif(p, base + timedelta(seconds=offset))
        paths.append(p)
        dts.append(base + timedelta(seconds=offset))

    labels, _ = cluster_series(
        paths,
        visual_enabled=False,
        exif_datetimes=dts,
        time_window_seconds=10,
    )
    assert labels[0] == labels[1] == labels[2] != -1
    assert labels[3] == -1


def test_time_chain_merges_transitively(tmp_path: Path) -> None:
    # A-B und B-C jeweils im Zeitfenster -> A, B, C eine Serie (Kette),
    # obwohl A-C (15 s) ausserhalb des Fensters liegt.
    base = datetime(2026, 9, 12, 12, 0, 0)
    paths, dts = [], []
    for offset in (0, 5, 15):
        p = tmp_path / f"IMG_{offset:04d}.JPG"
        _make_image(p)
        paths.append(p)
        dts.append(base + timedelta(seconds=offset))

    labels, _ = cluster_series(
        paths,
        visual_enabled=False,
        exif_datetimes=dts,
        time_window_seconds=10,
    )
    assert labels[0] == labels[1] == labels[2] != -1


def test_filename_sequence_groups_consecutive(tmp_path: Path) -> None:
    # Fallback greift: alle Bilder ohne EXIF-Zeit -> Nummern verbinden.
    paths = []
    for num in (1, 2, 3, 10):
        p = tmp_path / f"MST{num:05d}.JPG"
        _make_image(p, color="red")
        paths.append(p)

    labels, _ = cluster_series(
        paths,
        visual_enabled=False,
        exif_datetimes=[None, None, None, None],
        time_window_seconds=10,
        filename_numbers=[1, 2, 3, 10],
        max_filename_gap=2,
    )
    assert labels[0] == labels[1] == labels[2] != -1
    assert labels[3] == -1


def test_filename_sequence_ignored_when_exif_present(tmp_path: Path) -> None:
    # Fallback greift NICHT: Bilder mit EXIF-Zeit werden nicht per Nummer verkettet.
    base = datetime(2026, 9, 12, 10, 0, 0)
    paths, numbers, dts = [], [], []
    for num in (1, 2, 3):
        p = tmp_path / f"MST{num:05d}.JPG"
        _make_image(p, color="red")
        paths.append(p)
        numbers.append(num)
    dts = [base, base + timedelta(hours=1), base + timedelta(hours=2)]

    labels, _ = cluster_series(
        paths,
        visual_enabled=False,
        exif_datetimes=dts,
        time_window_seconds=10,
        filename_numbers=numbers,
        max_filename_gap=2,
    )
    assert labels == [-1, -1, -1]


def test_filename_fallback_groups_exifless_images(tmp_path: Path) -> None:
    # Positiv-Nachweis: EXIF-lose Bilder werden per Nummer verbunden,
    # Bilder mit EXIF-Zeit bleiben davon unberuehrt.
    base = datetime(2026, 9, 12, 10, 0, 0)
    paths, numbers, dts = [], [], []
    for num in (100, 101, 500):
        p = tmp_path / f"MST{num:05d}.JPG"
        _make_image(p)
        paths.append(p)
        numbers.append(num)
    dts = [None, None, base]

    labels, _ = cluster_series(
        paths,
        visual_enabled=False,
        exif_datetimes=dts,
        time_window_seconds=10,
        filename_numbers=numbers,
        max_filename_gap=2,
    )
    assert labels[0] == labels[1] != -1
    assert labels[2] == -1


def test_max_series_size_splits_large_group(tmp_path: Path) -> None:
    paths, numbers, dts = [], [], []
    for num in range(1, 31):
        p = tmp_path / f"MST{num:05d}.JPG"
        _make_image(p)
        paths.append(p)
        numbers.append(num)
        dts.append(None)

    labels, _ = cluster_series(
        paths,
        visual_enabled=False,
        exif_datetimes=dts,
        time_window_seconds=10,
        filename_numbers=numbers,
        max_filename_gap=1,
        max_series_size=10,
        min_samples=2,
    )
    counts = Counter(labels)
    assert -1 not in counts
    assert sorted(counts.values()) == [10, 10, 10]
