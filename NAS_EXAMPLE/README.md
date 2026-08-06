<!--
Projekt: Synology Photo Workflow
Pfad: NAS_EXAMPLE/TEMP
Rolle: TEMP
Funktion: Beschreibt Zweck, zulässige Daten und klare Abgrenzung dieses Ordners.
-->

# TEMP

Dieser Ordner ist der Arbeitsbereich des Workflows und bildet den persistenten Wurzelbereich für alle prozessnahen Daten. Er nimmt die Unterordner für Eingang, Review, Übergabe, Fehlerfälle und technische Laufzeitdaten auf. Hier entstehen keine Quellcodeartefakte, sondern ausschließlich Betriebsdaten, Manifeste, Summaries und Verzeichniszustände. Der Ordner ist die richtige Wahl, wenn Dateien vom Workflow verarbeitet, sortiert oder als Zustand dokumentiert werden sollen. Er darf nicht als Archiv für beliebige private Dateien verwendet werden; dafür sind die konkreten Unterordner oder externe Sicherungsorte vorgesehen.

## Abgrenzung

Dieser Ordner ist nicht der richtige Ort für Inhalte, die fachlich in einen vorgelagerten oder nachgelagerten Workflow-Schritt gehören. Wenn die Daten noch unverarbeitet sind, muss `TEMP_SD` verwendet werden. Wenn die Daten bereits als Phase-1-Ergebnis vorliegen, gehört der Inhalt nach `TEMP_IMAGES`. Wenn die Freigabe bereits manuell erfolgt ist, ist `TEMP_DONE` zuständig. Wenn eine Unsicherheit, ein Konflikt oder ein Sicherheitsproblem vorliegt, gehört der Fall nach `TEMP_ERROR`. Technische Laufzeitdaten, Modelle, Caches und Summaries gehören in `WORKFLOW_DATA`, nicht in die Eingangs- oder Review-Ordner.
