<!--
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

