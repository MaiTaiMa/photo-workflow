"""Regressionstest: EXIF-Orientierung muss im Face-Crop wirken."""
from PIL import Image, ImageOps

from app.faces.face_crop_generator import create_square_face_crop


def _red_box(image):
    px = image.load()
    xs, ys = [], []
    for y in range(image.height):
        for x in range(image.width):
            r, g, b = px[x, y][:3]
            if r > 200 and g < 80 and b < 80:
                xs.append(x)
                ys.append(y)
    assert xs, "Markierung nicht gefunden"
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def _red_pixels(image):
    px = image.load()
    return sum(
        1
        for y in range(image.height)
        for x in range(image.width)
        if px[x, y][0] > 200 and px[x, y][1] < 80 and px[x, y][2] < 80
    )


def test_crop_respects_exif_orientation_8(tmp_path) -> None:
    src = tmp_path / "orient8.jpg"
    img = Image.new("RGB", (400, 200), (15, 15, 15))
    for y in range(40):
        for x in range(40):
            img.putpixel((x, y), (255, 0, 0))
    exif = Image.Exif()
    exif[0x0112] = 8
    img.save(src, format="JPEG", exif=exif, quality=95)

    ref = ImageOps.exif_transpose(Image.open(src))
    l, t, r, b = _red_box(ref)
    box = {"left": max(0, l - 6), "top": max(0, t - 6),
           "right": min(ref.width, r + 6), "bottom": min(ref.height, b + 6)}

    out = tmp_path / "crop.jpg"
    create_square_face_crop(src, box, out, target_size=128, padding_ratio=0.2)
    assert _red_pixels(Image.open(out).convert("RGB")) > 0, \
        "Crop enthaelt die Markierung nicht (EXIF ignoriert?)"


def test_crop_unrotated_image_unchanged(tmp_path) -> None:
    src = tmp_path / "plain.jpg"
    img = Image.new("RGB", (300, 300), (15, 15, 15))
    for y in range(100, 140):
        for x in range(100, 140):
            img.putpixel((x, y), (255, 0, 0))
    img.save(src, format="JPEG", quality=95)
    box = {"left": 95, "top": 95, "right": 145, "bottom": 145}
    out = tmp_path / "crop.jpg"
    create_square_face_crop(src, box, out, target_size=128, padding_ratio=0.2)
    assert _red_pixels(Image.open(out).convert("RGB")) > 0
