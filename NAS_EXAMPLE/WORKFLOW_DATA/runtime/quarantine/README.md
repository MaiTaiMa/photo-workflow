<!-- Projekt: Synology Photo Workflow; Pfad: NAS_EXAMPLE/TEMP/WORKFLOW_DATA/runtime/quarantine/README.md; Rolle: Laufzeit-Quarantäne -->
# quarantine

Dieser Ordner sammelt technische Laufzeitfälle, die zwar während des Betriebs entstehen, aber nicht als regulärer Zustand weiterverarbeitet werden dürfen. Hier landen zum Beispiel Konflikte, blockierte Artefakte, Prüfverletzungen oder andere Ausnahmen, die im Lauf protokolliert und separat betrachtet werden müssen. Die Quarantäne hilft dabei, Fehler sichtbar zu machen, ohne sie in den normalen Betrieb zu mischen. Sie ist nicht für Eingangsdateien gedacht und ersetzt nicht `TEMP_ERROR`, das bereits den Eingang auf Batch-Ebene blockiert. Wenn das Problem vor der eigentlichen Verarbeitung entsteht, gehört es eher in `TEMP_ERROR`; wenn es während eines Laufes entsteht, ist `runtime/quarantine` der richtige Ort.

## Abgrenzung

Dieser Ordner ist nicht für Logs, normale Zustände oder Archivdateien vorgesehen. Logs gehören nach `runtime/logs`, Zustände nach `runtime/state` und Berichte nach `runtime/runsummaries`. Die Quarantäne dient nur der sicheren Trennung von problematischen technischen Artefakten.
