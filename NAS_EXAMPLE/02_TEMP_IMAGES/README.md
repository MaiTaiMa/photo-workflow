<!--
Projekt: Synology Photo Workflow
Pfad: NAS_EXAMPLE/TEMP/TEMP_IMAGES
Rolle: TEMP_IMAGES
Funktion: Beschreibt Zweck, zulässige Daten und klare Abgrenzung dieses Ordners.
-->

# TEMP_IMAGES

Dieser Ordner enthält das Ergebnis von Phase 1 und ist für die menschliche Sichtprüfung gedacht. Hier liegen die vom Workflow bewerteten und aufbereiteten Inhalte, mit denen ein Mensch die Qualität, die aktiven JPGs und die weitere Behandlung beurteilen kann. Der Ordner dokumentiert damit den Zwischenstand zwischen automatischer Bewertung und bewusster Freigabe. Er ist nicht für eine automatische Phase-2-Bereinigung geeignet, weil dort noch keine endgültige Übergabe stattgefunden hat. Wenn ein Batch bereits freigegeben werden soll, muss er aus diesem Bereich in TEMP_DONE überführt werden; blockierte oder fehlerhafte Fälle gehören dagegen nach TEMP_ERROR.

## Abgrenzung

Dieser Ordner ist nicht der richtige Ort für Inhalte, die fachlich in einen vorgelagerten oder nachgelagerten Workflow-Schritt gehören. Wenn die Daten noch unverarbeitet sind, muss `TEMP_SD` verwendet werden. Wenn die Daten bereits als Phase-1-Ergebnis vorliegen, gehört der Inhalt nach `TEMP_IMAGES`. Wenn die Freigabe bereits manuell erfolgt ist, ist `TEMP_DONE` zuständig. Wenn eine Unsicherheit, ein Konflikt oder ein Sicherheitsproblem vorliegt, gehört der Fall nach `TEMP_ERROR`. Technische Laufzeitdaten, Modelle, Caches und Summaries gehören in `WORKFLOW_DATA`, nicht in die Eingangs- oder Review-Ordner.
