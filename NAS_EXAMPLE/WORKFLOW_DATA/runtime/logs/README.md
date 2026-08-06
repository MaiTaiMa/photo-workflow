<!-- Projekt: Synology Photo Workflow; Pfad: NAS_EXAMPLE/TEMP/WORKFLOW_DATA/runtime/logs/README.md; Rolle: Laufzeitprotokolle -->
# logs

Dieser Ordner nimmt die technischen Laufzeitprotokolle des Workflows auf. Hier landen Ausgaben aus CLI, Scheduler, Recovery, Validierung und Fehlerbehandlung, soweit sie in den persistenten Datenbereich geschrieben werden. Die Protokolle dienen der Nachvollziehbarkeit und sind für Betrieb, Diagnose und Revision gedacht. Sie sind nicht für Eingangsdateien, Review-Bilder oder Modellartefakte vorgesehen. Wenn ein Inhalt ein Bild, ein Batch oder eine Referenz ist, gehört er nicht hierher, sondern in TEMP_SD, TEMP_IMAGES, WORKFLOW_DATA/samples oder WORKFLOW_DATA/models.

## Abgrenzung

Dieser Ordner ist nicht der Ort für States, Locks oder Quarantänefälle, die aktiv durch den Workflow verarbeitet werden. Zustandsdateien gehören nach `runtime/state`, Sperrdateien nach `runtime/locks` und technische Ausreißer nach `runtime/quarantine`. Logdaten sind rein beschreibend und sollen keine operative Verarbeitung ersetzen.
