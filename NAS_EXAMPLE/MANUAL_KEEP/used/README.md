<!--
Projekt: Synology Photo Workflow
Pfad: NAS_EXAMPLE/TEMP/MANUAL_KEEP/used
Rolle: MANUAL_KEEP/used
Funktion: Beschreibt Zweck, zulässige Daten und klare Abgrenzung dieses Ordners.
-->

# MANUAL_KEEP/used

Dieser Unterordner dokumentiert manuell bereits verwendete Keep-Dateien oder Zuordnungen. Er verhindert, dass dieselbe manuelle Auswahl unkontrolliert erneut verarbeitet oder fälschlich als neu betrachtet wird. Damit schafft der Ordner Nachvollziehbarkeit über den Lebenszyklus manueller Referenzen und schützt vor doppelter Nutzung. Er ist nicht für neue Eingänge oder offene Review-Fälle gedacht. Neue manuelle Entscheidungen gehören zuerst in MANUAL_KEEP/inbox; für normale Batch-Verarbeitung sind TEMP_SD, TEMP_IMAGES und TEMP_DONE zuständig.

## Abgrenzung

Dieser Ordner ist nicht der richtige Ort für Inhalte, die fachlich in einen vorgelagerten oder nachgelagerten Workflow-Schritt gehören. Wenn die Daten noch unverarbeitet sind, muss `TEMP_SD` verwendet werden. Wenn die Daten bereits als Phase-1-Ergebnis vorliegen, gehört der Inhalt nach `TEMP_IMAGES`. Wenn die Freigabe bereits manuell erfolgt ist, ist `TEMP_DONE` zuständig. Wenn eine Unsicherheit, ein Konflikt oder ein Sicherheitsproblem vorliegt, gehört der Fall nach `TEMP_ERROR`. Technische Laufzeitdaten, Modelle, Caches und Summaries gehören in `WORKFLOW_DATA`, nicht in die Eingangs- oder Review-Ordner.
