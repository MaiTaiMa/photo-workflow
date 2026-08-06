<!--
Projekt: Synology Photo Workflow
Pfad: NAS_EXAMPLE/TEMP/TEMP_DONE
Rolle: TEMP_DONE
Funktion: Beschreibt Zweck, zulässige Daten und klare Abgrenzung dieses Ordners.
-->

# TEMP_DONE

Dieser Ordner ist der kontrollierte Freigabepunkt zwischen Phase 1 und Phase 2. Nur Batches, die manuell geprüft und bewusst freigegeben wurden, sollen hier landen, damit Phase 2 sie weiterverarbeiten darf. Der Ordner dient damit als explizites Signal, dass der menschliche Review-Prozess abgeschlossen ist. Er ist nicht für ungesichtete Eingänge, Rohdaten oder temporäre Review-Ergebnisse gedacht. Wenn eine Freigabe noch aussteht, muss der Batch in TEMP_IMAGES bleiben; wenn ein Fehler vorliegt, ist TEMP_ERROR der richtige Ort.

## Abgrenzung

Dieser Ordner ist nicht der richtige Ort für Inhalte, die fachlich in einen vorgelagerten oder nachgelagerten Workflow-Schritt gehören. Wenn die Daten noch unverarbeitet sind, muss `TEMP_SD` verwendet werden. Wenn die Daten bereits als Phase-1-Ergebnis vorliegen, gehört der Inhalt nach `TEMP_IMAGES`. Wenn die Freigabe bereits manuell erfolgt ist, ist `TEMP_DONE` zuständig. Wenn eine Unsicherheit, ein Konflikt oder ein Sicherheitsproblem vorliegt, gehört der Fall nach `TEMP_ERROR`. Technische Laufzeitdaten, Modelle, Caches und Summaries gehören in `WORKFLOW_DATA`, nicht in die Eingangs- oder Review-Ordner.
