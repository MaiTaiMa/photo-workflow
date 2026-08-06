<!--
Projekt: Synology Photo Workflow
Pfad: NAS_EXAMPLE/TEMP/MANUAL_KEEP
Rolle: MANUAL_KEEP
Funktion: Beschreibt Zweck, zulässige Daten und klare Abgrenzung dieses Ordners.
-->

# MANUAL_KEEP

Dieser Ordner bündelt manuelle Keep-bezogene Zwischenstände und ist eng an die Review- und Referenzlogik des Projekts gekoppelt. Er hält Dateien oder Zuordnungen, die der Mensch ausdrücklich als besonders schützenswert, wiederverwendbar oder relevant markiert hat. Der Workflow nutzt diesen Bereich nicht für automatische Massenverschiebungen, sondern als kontrollierte Schnittstelle zur manuellen Bewertung. Er ist nicht für rohe Eingangsbatches oder allgemeine Reviews gedacht, weil dort die fachlichen Entscheidungen noch nicht getroffen wurden. Für Eingänge bleibt TEMP_SD zuständig, für Review TEMP_IMAGES und für freigegebene Übergänge TEMP_DONE.

## Abgrenzung

Dieser Ordner ist nicht der richtige Ort für Inhalte, die fachlich in einen vorgelagerten oder nachgelagerten Workflow-Schritt gehören. Wenn die Daten noch unverarbeitet sind, muss `TEMP_SD` verwendet werden. Wenn die Daten bereits als Phase-1-Ergebnis vorliegen, gehört der Inhalt nach `TEMP_IMAGES`. Wenn die Freigabe bereits manuell erfolgt ist, ist `TEMP_DONE` zuständig. Wenn eine Unsicherheit, ein Konflikt oder ein Sicherheitsproblem vorliegt, gehört der Fall nach `TEMP_ERROR`. Technische Laufzeitdaten, Modelle, Caches und Summaries gehören in `WORKFLOW_DATA`, nicht in die Eingangs- oder Review-Ordner.
