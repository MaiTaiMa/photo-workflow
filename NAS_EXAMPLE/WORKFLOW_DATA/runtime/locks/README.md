<!-- Projekt: Synology Photo Workflow; Pfad: NAS_EXAMPLE/TEMP/WORKFLOW_DATA/runtime/locks/README.md; Rolle: Laufzeit-Sperren -->
# locks

Dieser Ordner verwaltet die technischen Locks des Workflows. Hier werden Sperrdateien oder ähnliche Laufzeitmarker abgelegt, die parallele Ausführungen, Batch-Konflikte oder unkontrollierte Doppelstarts verhindern. Ein Lock ist kein Fehlerzustand, sondern ein Schutzmechanismus, der die Integrität eines laufenden Jobs wahrt. Er darf nicht manuell gelöscht werden, nur weil er stört; zuerst muss geklärt werden, ob noch ein echter Lauf aktiv ist oder ob ein sauber dokumentierter stale-Fall vorliegt. Wenn eine Situation eher eine technische Fehlverarbeitung als eine Sperre darstellt, gehört sie nicht hierher, sondern in `runtime/quarantine` oder in die Zustandslogik.

## Abgrenzung

Dieser Ordner ist nicht für Batchzustände oder Ergebnisberichte gedacht. Laufzustände gehören nach `runtime/state`, Berichte nach `runtime/runsummaries` und Quarantänefälle nach `runtime/quarantine`. Wenn ein Batch fortgesetzt werden soll, muss die Recovery-Logik in den fachlichen Modulen arbeiten; der Lock-Ordner selbst dient nur der Synchronisierung.
