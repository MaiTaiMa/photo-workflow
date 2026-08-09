<!--
Projekt: Synology Photo Workflow
Pfad: NAS_EXAMPLE/TEMP
Rolle: TEMP
Funktion: Beschreibt Zweck, zulässige Daten und klare Abgrenzung dieses Ordners.
-->

# TEMP

Dieser Ordner ist der Arbeitsbereich des Workflows und bildet den persistenten Wurzelbereich für alle prozessnahen Daten. Er nimmt die Unterordner für Eingang, Review, Übergabe, Fehlerfälle und technische Laufzeitdaten auf. Hier entstehen keine Quellcodeartefakte, sondern ausschließlich Betriebsdaten, Manifeste, Summaries und Verzeichniszustände. Der Ordner ist die richtige Wahl, wenn Dateien vom Workflow verarbeitet, sortiert oder als Zustand dokumentiert werden sollen. Er darf nicht als Archiv für beliebige private Dateien verwendet werden; dafür sind die konkreten Unterordner oder externe Sicherungsorte vorgesehen.

## Abgrenzung

Dieser Ordner ist nicht der richtige Ort für Inhalte, die fachlich in einen vorgelagerten oder nachgelagerten Workflow-Schritt gehören. Wenn die Daten noch unverarbeitet sind, muss `TEMP_SD` verwendet werden. Wenn die Daten bereits als Phase-1-Ergebnis vorliegen, gehört der Inhalt nach `TEMP_IMAGES`. Wenn die Freigabe bereits manuell erfolgt ist, ist `TEMP_DONE` zuständig. Wenn eine Unsicherheit, ein Konflikt oder ein Sicherheitsproblem vorliegt, gehört der Fall nach `TEMP_ERROR`. Technische Laufzeitdaten, Modelle, Caches und Summaries gehören in `WORKFLOW_DATA`, nicht in die Eingangs- oder Review-Ordner.

## Aufbau

NAS_EXAMPLE/
├── 00_TEMP_ERROR/
│   └── README.md
│
├── 01_TEMP_SD/
│   └── README.md
│
├── 02_TEMP_IMAGES/
│   └── README.md
│
├── 03_TEMP_DONE/
│   └── README.md
│
├── 04_TEMP_FINAL/                         # optional, nur bei lokaler Endprüfung
│   └── README.md
│
├── MANUAL_KEEP/
│   ├── inbox/
│   └── used/
│   └── README.md
│
└── WORKFLOW_DATA/
    ├── faces/
    │   ├── chris/
    │   │   ├── reference/                 # aktive Face-Crops
    │   │   ├── new_faces/                 # neue Vorschläge für Chris
    │   │   └── selection.json
    │   ├── daniel/
    │   │   ├── reference/
    │   │   ├── new_faces/
    │   │   └── selection.json
    │   ├── kind1/
    │   │   ├── reference/
    │   │   ├── new_faces/
    │   │   └── selection.json
    │   ├── kind2/
    │   │   ├── reference/                 # zunächst leer, Adapter pausiert
    │   │   ├── new_faces/
    │   │   └── selection.json
    │   ├── michele/
    │   │   ├── reference/
    │   │   ├── new_faces/
    │   │   └── selection.json
    │   ├── mutter/
    │   │   ├── reference/                 # zunächst leer, Adapter pausiert
    │   │   ├── new_faces/
    │   │   └── selection.json
    │   ├── nelly/
    │   │   ├── reference/
    │   │   ├── new_faces/
    │   │   └── selection.json
    │   ├── oma/
    │   │   ├── reference/
    │   │   ├── new_faces/
    │   │   └── selection.json
    │   ├── opa/
    │   │   ├── reference/
    │   │   ├── new_faces/
    │   │   └── selection.json
    │   └── vater/
    │       ├── reference/
    │       ├── new_faces/
    │       └── selection.json
    │
    ├── samples/
    │   ├── aesthetic_reference/
    │   │   ├── reference/                 # allgemeiner Stil / gute Fotos
    │   │   ├── new_refs/                  # begrenzte Stilvorschläge
    │   │   └── selection.json
    │   │
    │   └── personal_training/
    │       ├── reference/                 # bewusst aktivierte Lieblingsbilder
    │       ├── new_refs/                  # Vorschläge für persönlichen Geschmack
    │       └── selection.json             # Status + menschliche Entscheidung
    │
    ├── models/
    │   ├── clip/
    │   │   ├── config.json
    │   │   ├── model.safetensors
    │   │   ├── preprocessor_config.json
    │   │   ├── processor_config.json
    │   │   ├── tokenizer.json
    │   │   └── tokenizer_config.json
    │   ├── face/
    │   │   ├── face_detection_yunet_2023mar.onnx
    │   │   └── face_recognition_sface_2021dec.onnx
    │   ├── family_faces/                  # Laufcache, keine Embeddings persistent
    │   ├── reference_scoring/             # Stilreferenz-Cache
    │   └── taste/                         # persönlicher Score, Cache/Artefakte
    │
    ├── runtime/
    │   ├── calibration/
    │   │   └── batches/
    │   ├── locks/
    │   │   └── .script.lock
    │   ├── logs/
    │   │   ├── process.log
    │   │   └── error.log
    │   ├── quarantine/
    │   ├── run_summaries/
    │   └── state/
    │
    └── README.md
