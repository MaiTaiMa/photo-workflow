<!--
Projekt: Synology Photo Workflow
Pfad: NAS_EXAMPLE/TEMP/MANUAL_KEEP/inbox
Rolle: MANUAL_KEEP/inbox
Funktion: Beschreibt Zweck, zulässige Daten und klare Abgrenzung dieses Ordners.
-->

# MANUAL_KEEP/inbox

Dieser Unterordner nimmt neue manuelle Keep-Hinweise oder Dateien auf, die später in die kontrollierte Verwendung überführt werden sollen. Er ist der Eingangsbereich für menschliche Entscheidungen, nicht für automatische Sortierung. Hier landen Dateien, wenn sie bewusst als Kandidaten für spätere Nutzung, Schutz oder Referenzierung gesammelt werden. Der Ordner darf nicht als allgemeiner Speicher für beliebige JPGs oder RAWs genutzt werden, da sonst die Nachvollziehbarkeit verloren ginge. Nicht passende Eingänge gehören in TEMP_SD für neue Batches oder in TEMP_IMAGES für Phase-1-Review.

## Abgrenzung

Dieser Ordner ist nicht der richtige Ort für Inhalte, die fachlich in einen vorgelagerten oder nachgelagerten Workflow-Schritt gehören. Wenn die Daten noch unverarbeitet sind, muss `TEMP_SD` verwendet werden. Wenn die Daten bereits als Phase-1-Ergebnis vorliegen, gehört der Inhalt nach `TEMP_IMAGES`. Wenn die Freigabe bereits manuell erfolgt ist, ist `TEMP_DONE` zuständig. Wenn eine Unsicherheit, ein Konflikt oder ein Sicherheitsproblem vorliegt, gehört der Fall nach `TEMP_ERROR`. Technische Laufzeitdaten, Modelle, Caches und Summaries gehören in `WORKFLOW_DATA`, nicht in die Eingangs- oder Review-Ordner.
