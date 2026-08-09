"""Test für Feature-Vektor-basiertes MANUAL_KEEP-Matching."""

from pathlib import Path
import tempfile
import shutil
from app.manual_keep import (
    detect_manual_keep_images,
    extract_visual_features,
    cosine_similarity,
)


def test_feature_extraction():
    """Testet Feature-Extraktion."""
    # Testbild erstellen (oder existierendes verwenden)
    test_img = Path('/tmp/test_image.jpg')
    
    if test_img.exists():
        features = extract_visual_features(test_img)
        print(f"Feature-Vektor-Länge: {len(features)}")
        print(f"Erste 10 Werte: {features[:10]}")


def test_cosine_similarity():
    """Testet Kosinus-Ähnlichkeit."""
    # Zwei identische Vektoren
    vec_a = [1.0, 2.0, 3.0]
    vec_b = [1.0, 2.0, 3.0]
    
    similarity = cosine_similarity(vec_a, vec_b)
    print(f"Identische Vektoren: {similarity} (erwartet: 1.0)")
    
    # Zwei unähnliche Vektoren
    vec_c = [1.0, 0.0, 0.0]
    vec_d = [0.0, 1.0, 0.0]
    
    similarity = cosine_similarity(vec_c, vec_d)
    print(f"Unähnliche Vektoren: {similarity} (erwartet: 0.0)")


def test_manual_keep_matching():
    """Testet MANUAL_KEEP-Matching mit Feature-Vektoren."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Ordnerstruktur erstellen
        inbox = tmpdir / 'inbox'
        batch = tmpdir / 'batch'
        inbox.mkdir()
        batch.mkdir()
        
        # Testbilder kopieren (falls vorhanden)
        # ...
        
        # Matching testen
        images, status = detect_manual_keep_images(
            batch_path=batch,
            manual_keep_inbox=inbox,
            manual_keep_used=tmpdir / 'used',
            similarity_threshold=0.85,
        )
        
        print(f"Status: {status}")
        print(f"Matched: {len(images)} Bilder")


if __name__ == '__main__':
    test_feature_extraction()
    test_cosine_similarity()
    test_manual_keep_matching()