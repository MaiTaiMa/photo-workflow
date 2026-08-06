<!--
Projekt: Synology Photo Workflow
Pfad: NAS_EXAMPLE/TEMP/WORKFLOW_DATA/models
Rolle: models
Funktion: Beschreibt Zweck, zulaessige Daten und klare Abgrenzung dieses Ordners.
-->

# models

Dieser Ordner enthaelt die lokalen Modell-Gewichte fuer die optionalen KI-Backends des Workflows.
Inhalte duerfen ausschliesslich Modell-Dateien sein, die explizit in der `config.yaml` referenziert werden.
Personenbezogene Daten, Bilder oder Laufzeitartefakte gehoeren nicht in diesen Ordner.

## Unterordner

- **face/** – Gesichtserkennungs-Modelle (z. B. `face_detection_yunet_2023mar.onnx`, `face_recognition_sface_2021dec.onnx`)
- **taste/** – CLIP-Modell-Gewichte fuer den optionalen personal_score-Adapter (z. B. `model.safetensors`)

## Hinweis

Alle Dateien in diesem Ordner werden durch `.gitignore` vom Repository ausgeschlossen (`*.onnx`, `*.safetensors`, `*.bin` etc.).
Nur `.gitkeep`-Platzhalter und diese `README.md` sind im Repo sichtbar.

## Abgrenzung

Dieser Ordner ist nicht der richtige Ort fuer Inhalte, die fachlich in einen vorgelagerten oder nachgelagerten Workflow-Schritt gehoeren.
Wenn die Daten noch unverarbeitet sind, muss `TEMP_SD` verwendet werden.
Wenn die Daten bereits als Phase-1-Ergebnis vorliegen, gehoert der Inhalt nach `TEMP_IMAGES`.
Wenn die Freigabe bereits manuell erfolgt ist, ist `TEMP_DONE` zustaendig.
Wenn eine Unsicherheit, ein Konflikt oder ein Sicherheitsproblem vorliegt, gehoert der Fall nach `TEMP_ERROR`.
Technische Laufzeitdaten, Caches und Summaries gehoeren in `WORKFLOW_DATA/runtime`, nicht in diesen Ordner.
