<!--
Projekt: Synology Photo Workflow
Pfad: NAS_EXAMPLE/TEMP/WORKFLOW_DATA
Rolle: WORKFLOW_DATA
Funktion: Beschreibt Zweck, zulässige Daten und klare Abgrenzung dieses Ordners.
-->

# WORKFLOW_DATA

Dieser Ordner ist das technische Gedächtnis des Workflows und enthält die langlebigen Betriebsdaten. Hier werden Batch-Zustände, Run-Summaries, Archive, Kalibrierungsdaten, Referenzen, Modelle, Caches und sonstige technische Artefakte abgelegt. Der Inhalt dieses Ordners beeinflusst die Wiederaufnahme, die Nachvollziehbarkeit und die Modell- bzw. Bewertungsfunktion des Projekts. Er ist nicht für Eingangsdateien oder Sichtprüfungen gedacht, sondern ausschließlich für persistente technische Daten. Wenn Daten nur ein Eingangs- oder Review-Zwischenstand sind, gehören sie in TEMP_SD oder TEMP_IMAGES; wenn es sich um bestätigte Freigaben handelt, greift TEMP_DONE.

## Abgrenzung

Dieser Ordner ist nicht der richtige Ort für Inhalte, die fachlich in einen vorgelagerten oder nachgelagerten Workflow-Schritt gehören. Wenn die Daten noch unverarbeitet sind, muss `TEMP_SD` verwendet werden. Wenn die Daten bereits als Phase-1-Ergebnis vorliegen, gehört der Inhalt nach `TEMP_IMAGES`. Wenn die Freigabe bereits manuell erfolgt ist, ist `TEMP_DONE` zuständig. Wenn eine Unsicherheit, ein Konflikt oder ein Sicherheitsproblem vorliegt, gehört der Fall nach `TEMP_ERROR`. Technische Laufzeitdaten, Modelle, Caches und Summaries gehören in `WORKFLOW_DATA`, nicht in die Eingangs- oder Review-Ordner.
