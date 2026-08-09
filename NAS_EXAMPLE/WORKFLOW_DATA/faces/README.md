<!--
Projekt: Synology Photo Workflow
Pfad: NAS_EXAMPLE/WORKFLOW_DATA/faces
Rolle: faces
Funktion: Beschreibt Zweck, zulassige Daten und klare Abgrenzung dieses Ordners.
-->

# faces

Dieser Ordner enthält die personenbezogenen Referenzbilder für die familienspezifische Gesichtserkennung. Jede Person erhält einen eigenen Unterordner mit dem Namen als Ordnernamen (Slug). Die Referenzbilder dienen ausschließlich dem Familien-Erkennungsmodul und sind keine allgemeine Bildablage.

## Ordnerstruktur

```text
faces/
├── <personen-slug>/
│   ├── reference/
│   └── new_faces/
└── README.md
```

### `<personen-slug>`

Der Ordnername ist die stabile Kennung der Person. Er soll kurz, eindeutig und dauerhaft sein, zum Beispiel:

- `Vater`
- `Mutter`
- `Kind1`
- `Kind2`
- `Oma`
- `Opa`
- `Chris`
- `Daniel`

Die Ordnernamen werden später für Tags wie `person:Vater`, `person:Oma` oder `person:Chris` verwendet. Wird ein Personenordner umbenannt, gilt dies als strukturelle Änderung: Bestehende Verweise, Referenzen und gegebenenfalls Auswahl- oder Pooldaten müssen anschließend geprüft werden.

## `reference/`

`reference/` enthält ausschließlich bewusst freigegebene Referenzbilder der jeweiligen Person. Diese Bilder bilden den aktiven Referenzbestand für die Erkennung.

**Empfehlung:**

- 10 bis 30 klare JPG-Bilder pro Person
- Möglichst verschiedene Blickwinkel und Lichtbedingungen
- Pro Bild möglichst nur das relevante Hauptgesicht
- Referenzen werden manuell ausgewählt

**Nicht erlaubt:** Platzhalter, Screenshots, Textdateien, Logs, Embeddings oder Metadaten-Dateien.

## `new_faces/`

`new_faces/` ist die kontrollierte Ablage für automatisch erzeugte oder zur Prüfung vorgeschlagene Gesichtsausschnitte. Dateien in diesem Ordner sind **noch keine** aktiven Referenzen und dürfen nicht als verbindliche Grundlage für die Zuordnung verwendet werden.

Nach manueller Prüfung kann ein geeigneter Ausschnitt nach `reference/` übernommen werden. Nicht passende, doppelte oder unklare Vorschlä�³e sollten nach der Prüfung entfernt werden.

## Reihenfolge der Referenzen

Die fachliche Reihenfolge ergibt sich nicht aus dem Dateinamen. Alle Bilder in `reference/` eines Personenordners gehören gleichrangig zum Referenzbestand; ein Dateiname darf daher weder Prioritat noch Freigabestatus ausdrucken.

Fur eine reproduzierbare Verarbeitung werden Dateien innerhalb eines Ordners stabil nach ihrem relativen Pfad bzw. Dateinamen in aufsteigender alphabetischer Reihenfolge verarbeitet. Diese technische Reihenfolge ist keine Qualitatsrangfolge.

Dateinamen sollen moglichst aus dem ursprunglichen Bildnamen abgeleitet bleiben. Der Personenordner liefert die Zuordnung zur Person; die Dateinamen mussen deshalb keinen Personennamen oder Rang enthalten. Neue Referenzen durfen hinzugefugt werden, ohne vorhandene Dateien umzubenennen oder still zu uberschreiben.

## Abgrenzung

Dieser Ordner ist nicht der richtige Ort fur Inhalte, die fachlich in einen vorgelagerten oder nachgelagerten Workflow-Schritt gehoren:

- Wenn die Daten noch unverarbeitet sind, muss `TEMP_SD` verwendet werden.
- Wenn die Daten im Review sind, gehort der Inhalt nach `TEMP_IMAGES`.
- Wenn ein Fehler, Konflikt oder Sicherheitsproblem vorliegt, gehort der Fall nach `TEMP_ERROR`.
- Technische Laufzeitdaten, Modelle, Caches und Summaries gehoren in `WORKFLOW_DATA/models/` bzw. `WORKFLOW_DATA/runtime/`, nicht in die Gesichtsordner.

Ein fehlender oder leerer `reference/`-Ordner ist zulassig, bedeutet aber, dass fur diese Person noch keine freigegebenen Referenzen verfugbar sind. Ein leerer `new_faces/`-Ordner ist der Normalzustand, solange keine neuen Vorschlage zur manuellen Prufung vorliegen.<!--
Projekt: Synology Photo Workflow
Pfad: NAS_EXAMPLE/TEMP/WORKFLOW_DATA/faces
Rolle: faces
Funktion: Beschreibt Zweck, zulässige Daten und klare Abgrenzung dieses Ordners.
-->

# faces

Lege pro Person mehrere Beispielbilder in den jeweiligen Unterordner.
Empfehlung:
- 10 bis 30 klare JPG-Bilder pro Person
- möglichst verschiedene Blickwinkel und Lichtbedingungen
- pro Bild möglichst nur das relevante Hauptgesicht

Beispiel:
- faces/Vater/
- faces/Mutter/
- faces/Kind1/
- faces/Kind2/

Diese Referenzbilder dienen ausschließlich dem Familien-Erkennungsmodul.

## Weitere Beispielpersonen
Zusätzlich zu `Vater`, `Mutter`, `Kind1` und `Kind2` kannst du auch weitere Personen wie `Oma` oder `Opa` als eigene Unterordner anlegen.
Die Ordnernamen werden später für Tags wie `person:Oma` oder `person:Opa` verwendet.

## Abgrenzung

Dieser Ordner ist nicht der richtige Ort für Inhalte, die fachlich in einen vorgelagerten oder nachgelagerten Workflow-Schritt gehören. Wenn die Daten noch unverarbeitet sind, muss `TEMP_SD` verwendet werden. Wenn die Daten bereits als Phase-1-Ergebnis vorliegen, gehört der Inhalt nach `TEMP_IMAGES`. Wenn die Freigabe bereits manuell erfolgt ist, ist `TEMP_DONE` zuständig. Wenn eine Unsicherheit, ein Konflikt oder ein Sicherheitsproblem vorliegt, gehört der Fall nach `TEMP_ERROR`. Technische Laufzeitdaten, Modelle, Caches und Summaries gehören in `WORKFLOW_DATA`, nicht in die Eingangs- oder Review-Ordner.

