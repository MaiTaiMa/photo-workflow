<!--
Projekt: Synology Photo Workflow
Pfad: NAS_EXAMPLE/TEMP/TEMP_ERROR
Rolle: TEMP_ERROR
Funktion: Beschreibt Zweck, zulässige Daten und klare Abgrenzung dieses Ordners.
-->

# TEMP_ERROR

Dieser Ordner ist die Quarantäne für blockierte, fehlerhafte oder unklare Batches. Hierhin gehören Eingänge, die wegen unvollständiger Kopien, ungültiger Struktur, Prüfkonflikten oder anderen Sicherheitsproblemen nicht weiterverarbeitet werden dürfen. Der Ordner verhindert, dass unsichere Daten versehentlich in den regulären Fluss gelangen. Er darf nicht als Ersatz für TEMP_IMAGES oder TEMP_DONE verwendet werden, weil dort keine Review- oder Freigabelogik stattfindet. Für reguläre Review-Zwischenstände ist TEMP_IMAGES zuständig, und für freigegebene Batches TEMP_DONE.

## Abgrenzung

Dieser Ordner ist nicht der richtige Ort für Inhalte, die fachlich in einen vorgelagerten oder nachgelagerten Workflow-Schritt gehören. Wenn die Daten noch unverarbeitet sind, muss `TEMP_SD` verwendet werden. Wenn die Daten bereits als Phase-1-Ergebnis vorliegen, gehört der Inhalt nach `TEMP_IMAGES`. Wenn die Freigabe bereits manuell erfolgt ist, ist `TEMP_DONE` zuständig. Wenn eine Unsicherheit, ein Konflikt oder ein Sicherheitsproblem vorliegt, gehört der Fall nach `TEMP_ERROR`. Technische Laufzeitdaten, Modelle, Caches und Summaries gehören in `WORKFLOW_DATA`, nicht in die Eingangs- oder Review-Ordner.
