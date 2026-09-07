"""Regressionstest: AppliedToDimensions in EXIF-angewandter Sicht."""
from PIL import Image

from app.family_recognition import _applied_dimensions


def test_applied_dimensions_exif8(tmp_path) -> None:
    img = Image.new("RGB", (400, 200), (15, 15, 15))
    exif = Image.Exif()
    exif[0x0112] = 8
    src = tmp_path / "o8.jpg"
    img.save(src, format="JPEG", exif=exif, quality=95)
    assert _applied_dimensions(src) == (200, 400)


def test_applied_dimensions_plain(tmp_path) -> None:
    src = tmp_path / "p.jpg"
    Image.new("RGB", (400, 200)).save(src, format="JPEG", quality=95)
    assert _applied_dimensions(src) == (400, 200)
