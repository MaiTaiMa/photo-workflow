<!--
Projekt: Synology Photo Workflow
Pfad: NAS_EXAMPLE/TEMP/TEMP_SD
Rolle: TEMP_SD
Funktion: Beschreibt Zweck, zulässige Daten und klare Abgrenzung dieses Ordners.
-->

# TEMP_SD

Dieser Ordner nimmt neue Kamera- oder Gerätebatches auf und ist der Eingangspunkt für Phase 1. Hier werden vollständige, noch unverarbeitete Batch-Ordner abgelegt, typischerweise mit einem klaren Namen wie einem Datum oder einer anderen stabilen Kennung. Der Workflow erwartet hier die Rohdaten, die noch nicht manuell freigegeben oder in Review überführt wurden. In diesem Ordner entstehen Inventarinformationen und Zustandsprüfungen, aber keine finale Freigabe. Er darf nicht für bereits geprüfte Ergebnisse genutzt werden; dafür sind TEMP_IMAGES oder TEMP_DONE vorgesehen, je nachdem ob nur Sichtprüfung oder bereits manuelle Freigabe erfolgt ist.

## Abgrenzung

Dieser Ordner ist nicht der richtige Ort für Inhalte, die fachlich in einen vorgelagerten oder nachgelagerten Workflow-Schritt gehören. Wenn die Daten noch unverarbeitet sind, muss `TEMP_SD` verwendet werden. Wenn die Daten bereits als Phase-1-Ergebnis vorliegen, gehört der Inhalt nach `TEMP_IMAGES`. Wenn die Freigabe bereits manuell erfolgt ist, ist `TEMP_DONE` zuständig. Wenn eine Unsicherheit, ein Konflikt oder ein Sicherheitsproblem vorliegt, gehört der Fall nach `TEMP_ERROR`. Technische Laufzeitdaten, Modelle, Caches und Summaries gehören in `WORKFLOW_DATA`, nicht in die Eingangs- oder Review-Ordner.
