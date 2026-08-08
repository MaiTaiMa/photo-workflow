from __future__ import annotations

from pathlib import Path

from .protocol import BackendInfo


class HuggingFaceFaceBackend:
    """Local embedding adapter; model bytes and embeddings never enter workflow data."""

    def __init__(self, model_id: str = "anjith2006/edgeface",
                 subfolder: str = "edgeface-xxs", device: str = "cpu"):
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

    def _load(self):
        if self._model is not None:
            return
        import torch
        from transformers import AutoImageProcessor, AutoModel
        self._torch = torch
        self._processor = AutoImageProcessor.from_pretrained(
            self.model_id, subfolder=self.subfolder)
        self._model = AutoModel.from_pretrained(
            self.model_id, subfolder=self.subfolder).to(self.device).eval()

    def embedding(self, image_path: str):
        from PIL import Image
        self._load()
        image = Image.open(Path(image_path)).convert("RGB")
        inputs = self._processor(images=image, return_tensors="pt")
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with self._torch.no_grad():
            output = self._model(**inputs)
            vector = getattr(output, "embeddings", None)
            if vector is None:
                vector = output.pooler_output
            vector = vector[0]
            vector = vector / self._torch.linalg.vector_norm(vector)
        return vector.detach().cpu().numpy()
