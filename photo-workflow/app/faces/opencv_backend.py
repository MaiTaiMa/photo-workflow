# =============================================================================
# PROJECT:     photo-workflow
# FILE:        app/faces/opencv_backend.py
# PURPOSE:     Erkennt Gesichter mit YuNet und erzeugt SFace-Embeddings.
# AUTHOR:      Matzethias
# DATE:        2026-08-09
# VERSION:     1.0
# REQUIRES:    Python 3.11, OpenCV-Contrib, NumPy
# CHANGES:
#   2026-08-09 | 1.0 | YuNet, SFace und RAM-only Face-Pipeline ergänzt
# =============================================================================


from __future__ import annotations

# === Standardbibliothek ===
# Zweck: Lädt Modellpfade und berechnet reproduzierbare Modellmetadaten.
# Eingabe: Config und lokale Bilddateien.
# Ausgabe: Face-Detections und flüchtige SFace-Embeddings.
import hashlib
from pathlib import Path

import cv2
import numpy as np

from .protocol import BackendInfo


def configure_dnn_backend(preferred_target=None) -> None:
    """
    Konfiguriere DNN-Backend mit Graceful Degradation für OpenCV 5.x
    
    Diese Funktion sollte VOR dem Laden von DNN-Modellen aufgerufen werden.
    
    Args:
        preferred_target: Bevorzugtes Target (CPU, GPU, VPU, etc.)
    """
    if preferred_target is None:
        preferred_target = cv2.dnn.DNN_TARGET_CPU
    
    opencv_version = tuple(map(int, cv2.__version__.split('.')[:3]))
    
    # OpenCV 5.x: Target-Setzung wird nicht unterstützt, aber wir versuchen es trotzdem
    # mit Graceful Degradation
    if opencv_version >= (5, 0, 0):
        # Backend explizit setzen (falls verfügbar)
        if hasattr(cv2.dnn, 'DNN_BACKEND_OPENCV'):
            try:
                cv2.dnn.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            except Exception:
                pass  # Graceful Degradation
        
        # Target-Setzung in 5.x wird gewarnt, aber wir akzeptieren den CPU-Fallback
        if hasattr(cv2.dnn, 'DNN_TARGET_CPU'):
            try:
                cv2.dnn.setPreferableTarget(preferred_target)
            except Exception:
                pass  # Erwartet in 5.x - wir fahren fort
    else:
        # OpenCV < 5.0: Target setzen wie gewohnt
        if hasattr(cv2.dnn, 'setPreferableTarget'):
            cv2.dnn.setPreferableTarget(preferred_target)

# Beim ersten Aufruf einmalig konfigurieren
_configure_dnn_called = False

def _ensure_dnn_configured() -> None:
    """Stelle sicher, dass DNN-Backend nur einmal konfiguriert wird."""
    global _configure_dnn_called
    if not _configure_dnn_called:
        configure_dnn_backend()
        _configure_dnn_called = True



class OpenCVFaceBackend:
    """
    Lokaler YuNet-/SFace-Adapter mit proportionaler Bildskalierung.

    Bildbytes und Embeddings bleiben während des Aufrufs im RAM.
    Die Detection-Koordinaten werden auf die Originalgröße zurückgeführt.
    """

    def __init__(self, config: dict):
        """Initialisiert YuNet, SFace und die konfigurierten Schwellenwerte."""
        models = config.get("models", {})
        detection = models.get("face_detection", {})
        recognition = models.get("face_recognition", {})

        self.yunet_path = Path(detection["model_path"]).expanduser().resolve()
        self.sface_path = Path(recognition["model_path"]).expanduser().resolve()
        self.threshold = float(detection.get("confidence_threshold", 0.65))
        self.nms_threshold = float(detection.get("nms_threshold", 0.3))
        self.top_k = int(detection.get("top_k", 5000))
        self.max_input_side = int(detection.get("max_input_side", 1600))

        self._detector = None
        self._recognizer = None
        self.info = BackendInfo(
            registry_id="opencv-yunet-sface-v1",
            adapter_name="OpenCVFaceBackend",
            model_hash=self._model_hash(),
            provider="opencv",
            preprocessing=f"max_side={self.max_input_side}",
            metric=str(recognition.get("distance_metric", "cosine")),
            selection_fingerprint="opencv-yunet-sface-v1",
        )

    def _model_hash(self) -> str:
        """Erzeugt einen stabilen Hash aus den lokalen Modellmetadaten."""
        payload = []
        for path in (self.yunet_path, self.sface_path):
            stat = path.stat()
            payload.append(f"{path}:{stat.st_size}:{stat.st_mtime_ns}")
        return hashlib.sha256("\n".join(payload).encode()).hexdigest()

    def _load(self) -> None:
        """Lädt die OpenCV-Modelle verzögert beim ersten Aufruf."""
        _ensure_dnn_configured()
        if self._detector is not None:
            return
        self._detector = cv2.FaceDetectorYN.create(
            str(self.yunet_path),
            "",
            (320, 320),
            self.threshold,
            self.nms_threshold,
            self.top_k,
        )
        self._recognizer = cv2.FaceRecognizerSF.create(
            str(self.sface_path),
            "",
        )

    def _analysis_image(self, image: np.ndarray) -> tuple[np.ndarray, float]:
        """Skaliert ein Bild proportional auf die konfigurierte Maximalgröße."""
        height, width = image.shape[:2]
        scale = min(1.0, self.max_input_side / max(width, height))
        if scale >= 1.0:
            return image, scale
        resized = cv2.resize(
            image,
            (int(width * scale), int(height * scale)),
            interpolation=cv2.INTER_AREA,
        )
        return resized, scale

    def detect(self, image_path: str | Path) -> list[dict]:
        """
        Erkennt Gesichter und gibt Boxen sowie Landmarken in Originalkoordinaten zurück.
        """
        self._load()
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"Image cannot be read: {image_path}")

        analysis, scale = self._analysis_image(image)
        height, width = analysis.shape[:2]
        self._detector.setInputSize((width, height))
        _, faces = self._detector.detect(analysis)
        if faces is None:
            return []

        results = []
        for face in faces:
            values = face.astype(float).copy()
            if scale < 1.0:
                values[:14] /= scale
            x, y, box_width, box_height = values[:4]
            landmarks = values[4:14].reshape(5, 2).tolist()
            results.append({
                "box": {
                    "left": int(round(x)),
                    "top": int(round(y)),
                    "right": int(round(x + box_width)),
                    "bottom": int(round(y + box_height)),
                },
                "landmarks": landmarks,
                "confidence": float(values[14]),
            })
        return results

    def embeddings(self, image_path: str | Path) -> list[tuple[np.ndarray, dict]]:
        """Erzeugt ein flüchtiges SFace-Embedding je erkanntem Gesicht."""
        self._load()
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"Image cannot be read: {image_path}")

        detections = self.detect(image_path)
        values = []
        for detection in detections:
            box = detection["box"]
            face = np.array(
                [
                    box["left"],
                    box["top"],
                    box["right"] - box["left"],
                    box["bottom"] - box["top"],
                    *sum(detection["landmarks"], []),
                    detection["confidence"],
                ],
                dtype=np.float32,
            )
            aligned = self._recognizer.alignCrop(image, face)
            feature = self._recognizer.feature(aligned)
            values.append((feature.reshape(-1), detection))
        return values

    def embedding(self, image_path: str) -> np.ndarray:
        """Erzeugt das erste Gesichtsembedding eines Bildes im RAM."""
        values = self.embeddings(image_path)
        if not values:
            raise ValueError(f"No face detected: {image_path}")
        return values[0][0]