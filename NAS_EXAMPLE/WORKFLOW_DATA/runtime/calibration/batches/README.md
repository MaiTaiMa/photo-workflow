<!--
Projekt: Synology Photo Workflow
Pfad: NAS_EXAMPLE/TEMP/WORKFLOW_DATA/runtime/calibration/batches
Rolle: batches
Funktion: Beschreibt Zweck, zulässige Daten und klare Abgrenzung dieses Ordners.
-->

# batches

Dieser Ordner gehört zur persistenten NAS-Beispielstruktur des Projekts und erfüllt eine klar abgegrenzte Rolle innerhalb des Workflows. Er speichert Daten oder Zustände, die von den benachbarten Bereichen logisch getrennt bleiben müssen, damit der Ablauf reproduzierbar und sicher bleibt. In diesem Ordner dürfen nur Inhalte liegen, die fachlich zu seiner beschriebenen Aufgabe passen, beispielsweise Zustände, Review-Artefakte oder Referenzen. Wenn eine Datei noch Eingangsdaten oder ein unfreigegebener Zwischenstand ist, gehört sie in den jeweils vorgelagerten Bereich, nicht hierher. Wenn eine Datei bereits freigegeben, geprüft oder als Laufzeitartefakt persistiert werden soll, muss sie in den dafür vorgesehenen Ordner des Workflows verschoben werden.

## Abgrenzung

Dieser Ordner ist nicht der richtige Ort für Inhalte, die fachlich in einen vorgelagerten oder nachgelagerten Workflow-Schritt gehören. Wenn die Daten noch unverarbeitet sind, muss `TEMP_SD` verwendet werden. Wenn die Daten bereits als Phase-1-Ergebnis vorliegen, gehört der Inhalt nach `TEMP_IMAGES`. Wenn die Freigabe bereits manuell erfolgt ist, ist `TEMP_DONE` zuständig. Wenn eine Unsicherheit, ein Konflikt oder ein Sicherheitsproblem vorliegt, gehört der Fall nach `TEMP_ERROR`. Technische Laufzeitdaten, Modelle, Caches und Summaries gehören in `WORKFLOW_DATA`, nicht in die Eingangs- oder Review-Ordner.
