"""
Skript: app/faces/huggingface_backend.py
Zweck: Stellt einen lokalen Hugging-Face-Embedding-Adapter bereit.
Autor: MaiTaiMa
Erstellt: 2026-08-08
Version: 1.2
Requires: Python 3.11, PyTorch, Transformers, Pillow

Änderungsprotokoll:
  2026-08-08 | 1.2 | AP22 Face-Backend nach 98AP formatiert
"""

from __future__ import annotations

# === Standardbibliothek ===
# Zweck: Beschreibt lokale Modellpfade und Adaptermetadaten.
# Eingabe: Bildpfad und Hugging-Face-Modellkonfiguration.
# Ausgabe: Flüchtiges normiertes Embedding.
from pathlib import Path

from .protocol import BackendInfo


class HuggingFaceFaceBackend:
    """
    Lokaler Embedding-Adapter ohne persistente Bild- oder Vektordaten.

    Modell- und Embeddingdaten werden nur während der aktiven Verarbeitung
    im Speicher gehalten.
    """

    def __init__(
        self,
        model_id: str = "anjith2006/edgeface",
        subfolder: str = "edgeface-xxs",
        device: str = "cpu",
    ):
        """Initialisiert Modellreferenz, Unterordner und Rechengerät."""
        self.model_id = model_id
        self.subfolder = subfolder
        self.device = device
        self._torch = None
        self._processor = None
        self._model = None
        self.info = BackendInfo(
            registry_id="huggingface-edgeface-v1",
            adapter_name="HuggingFaceFaceBackend",
            model_hash=model_id,
            provider=device,
            preprocessing="model-native-image-processor",
            metric="cosine_distance",
            selection_fingerprint=subfolder,
        )

    def _load(self) -> None:
        """Lädt Processor und Modell verzögert beim ersten Embedding-Aufruf."""
        if self._model is not None:
            return

        import torch
        from transformers import AutoImageProcessor, AutoModel

        self._torch = torch
        self._processor = AutoImageProcessor.from_pretrained(
            self.model_id,
            subfolder=self.subfolder,
        )
        self._model = AutoModel.from_pretrained(
            self.model_id,
            subfolder=self.subfolder,
        ).to(self.device).eval()

    def embedding(self, image_path: str):
        """
        Erzeugt ein normiertes Embedding für ein Bild.

        Das Bild und der Vektor werden nicht in Workflow-Artefakte geschrieben.
        """
        from PIL import Image

        self._load()
        with Image.open(Path(image_path)) as image:
            rgb_image = image.convert("RGB")

        inputs = self._processor(
            images=rgb_image,
            return_tensors="pt",
        )
        inputs = {
            key: value.to(self.device)
            for key, value in inputs.items()
        }
        with self._torch.no_grad():
            output = self._model(**inputs)
            vector = getattr(output, "embeddings", None)
            if vector is None:
                vector = output.pooler_output
            vector = vector[0]
            vector = vector / self._torch.linalg.vector_norm(vector)

        return vector.detach().cpu().numpy()
