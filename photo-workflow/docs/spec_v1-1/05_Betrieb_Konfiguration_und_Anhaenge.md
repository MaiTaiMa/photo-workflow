# 6. Betrieb, Konfiguration, Reporting, Abnahme

## 6.1 Konfiguration

- **Schema:** YAML mit strikter Validierung; unbekannte Schlüssel sind Fehler (außer `extensions`).
- **Fingerprint:** Effektive Konfiguration wird mit SHA256-Fingerprint im Run dokumentiert.
- **Sicherheit:** Keine Geheimnisse, keine Produktionspfade in Git.
- **Config-Schlüssel:** Durchgängig snake_case.

## 6.2 Betrieb

- **Scheduler:** Container mit persistentem NAS-Mount starten; globaler Lock verhindert parallele Läufe.
- **Fehlerisolation:** Ein defekter Batch wird quarantänisiert statt den ganzen Lauf zu stoppen.
- **Ressourcenverhalten:** Auf Ziel-NAS dokumentieren.
- **Not-Stop:** Bei Zeitbudget oder SIGTERM keinen neuen teuren Schritt beginnen; sicheren aktuellen Schritt abschließen, Status `paused` atomar schreiben, kontrolliert beenden.

## 6.3 Reporting

- **Status:** Pflicht.
- **Zweck:** Macht jedem Lauf auf einen Blick klar, was passiert ist und was der Mensch tun muss.
- **Ablauf:** JSON-Run-Summary, Scheduler-Ausgabe, CSV, Logs, `user_actions_required`.

## 6.4 Abnahme

Die Implementierung ist nur abnahmefähig, wenn mindestens folgende Prüfungen erfolgreich sind:

- `batch_id` wird durchgängig verwendet; `batchid` kommt nicht mehr vor.
- `paths.publish_root` und `target_folder` werden separat und kanonisch validiert.
- `04_TEMP_FINAL` ist vorhanden und seine Rolle in PHASE3 ist eindeutig beschrieben.
- `phase1_moving` ist im Zustandsweg enthalten.
- Stilles Scoring ist definiert und verboten.
- `review_state_invalid` verhindert jede ARW-Aktion.
- Das JPG-Sicherungs-ZIP enthält alle JPGs aus Hauptordner, `Review` und `Rejected`.
- Das ARW-Entscheidungs-ZIP wird vor jeder geschützten ARW-Löschung verifiziert.
- Ein `move` setzt `copy → verify → source removal` um.
- PHASE3 ist bei deaktivierter Veröffentlichung dateilos.
- Index-Timeouts sind resume-fähig.
- API-Secrets werden ausschließlich über Umgebungsvariablen bereitgestellt.
- Unbekannte Gesichter und Embeddings werden nicht unzulässig persistent gespeichert.
- Face-Crops werden automatisch nur in `new_faces` gespeichert und nur manuell nach `reference` aktiviert.
- `unknown` ist ausschließlich im Recovery-Fall zulässig.
- Bei `min_active` wird nur der betroffene Adapter pausiert; sein Score ist `null`.
- Eine Referenzpooländerung invalidiert den RAM-Cache und löst einen Rebuild aus.

## 7. Stil- und Formatvereinheitlichung

- Überschriften als Markdown-Header.
- Listen mit Bindestrichen.
- Tabellen mit Header und Trennlinie.
- Codeblöcke mit Sprachangabe.
- Zitate mit `>`.

## 8. Wichtige Regeln

1. Git enthält nie Modellgewichte, private Bilder, Referenzen, Face-Crops, Embeddings, Laufzeitdaten, Caches, Logs oder Secrets.
2. NAS enthält alle Workflow-Daten und Konfiguration mit Produktionspfaden.
3. Docker-Container enthält nur Code und mountet NAS-Pfade.

## Anhang A — Skript-Anforderungen

### A1 – Geltungsbereich

Diese Anforderung gilt für alle Skript-Dateien im Repository.

### A2 – Struktur-Anforderungen

Jede Skript-Datei muss eine feste Struktur haben:

1. Header-Kommentar (6–10 Zeilen).
2. Abschnitts-Kommentare (2–3 Zeilen pro Abschnitt).
3. Funktions-Kommentare (3–5 Zeilen pro Funktion).
4. Einzeiler-Kommentare für komplexe Bedingungen.

### A3 – Kommentar-Dichte und Lesbarkeit

- Header: 6–10 Zeilen.
- Jede Funktion: 3–5 Zeilen Kommentar.
- Jeder Abschnitt: 2–3 Zeilen Kommentar.
- Ca. 20 % Kommentare im Skript.
- Sprechende Namen, konsistente Formatierung, max. 80–100 Zeichen pro Zeile.

### A4 – Beispiel-Header

```bash
#!/bin/bash
#
# Skript: scripts/run-phase1.sh
# Zweck: Führt Phase 1 für einen Batch aus (Inventar, Culling, Metadaten)
# Autor: MaiTaiMa
# Erstellt: 2026-08-04
# Version: 1.0
# Requires: bash, docker, exiftool
# Usage: ./run-phase1.sh <batch-id>
#
# Änderungsprotokoll:
#   2026-08-04 | v1.0 | Initiale Version
#
```

### A5 – Beispiel-Abschnitt

```bash
# === Validierung: Pflichtargumente prüfen ===
# Zweck: Stellt sicher, dass alle erforderlichen Argumente übergeben wurden
# Eingabe: $1 (BATCH_ID)
# Ausgabe: Fehlermeldung bei fehlendem Argument, Abbruch mit Exit-Code 1
if [ -z "$BATCH_ID" ]; then
    echo "Fehler: BATCH_ID ist erforderlich"
    echo "Usage: ./run-phase1.sh <batch-id>"
    exit 1
fi
```

### A6 – Beispiel-Betriebsfunktion

```bash
# === Betriebsprüfung und CLI-Start ===
# Zweck: Prüft NAS-Mount und startet ausschließlich die Python-CLI.
# Fachlogik für Dateien, Scores, Manifeste und Archive liegt in Python.
mountpoint -q "$WORKFLOW_BASEDIR" || {
    echo "Fehler: NAS-Mount fehlt"
    exit 2
}

docker compose run --rm workflow \
    python -m app.cli phase1 \
    --config /config/config.yaml \
    --batch-id "$BATCH_ID"
```

### A7 – Validierung und Abnahme

- Header-Kommentar vorhanden?
- Abschnitts-Kommentare vorhanden?
- Funktions-Kommentare vorhanden?
- Ca. 20 % Kommentare?
- Sprechende Namen?
- Konsistente Formatierung?

Bei Fehlern: Skript ungültig markieren, loggen, manuelle Korrektur.

### A8 – Versionierung und Änderungshistorie

- Jede Skript-Datei braucht Versionsnummer im Header.
- Jede Änderung muss im Header dokumentiert werden.
- Jede Änderung muss zusätzlich im CHANGELOG.md dokumentiert werden.

## Anhang B — Config-Anforderungen

### B1 – Geltungsbereich

Diese Anforderung gilt für alle Config-Dateien im Repository (`config.yaml` sowie erklärte Varianten wie `config.explained.yaml`).

### B2 – Struktur-Anforderungen

Jede Config-Datei muss eine feste Struktur haben:

1. Projekt-Header (4–6 Zeilen, einmalig am Dateianfang).
2. Logikblock-Kommentare vor jedem Funktionsblock (3–6 Zeilen, mit Trennlinien).
3. Variablen-Kommentare (3 Zeilen pro Variable: Zweck, Mögliche Werte, Auswirkung).
4. Zusatzzeilen für komplexe Variablen (`Voraussetzung:`, `Hinweis:`).

### B3 – Kommentar-Dichte und Lesbarkeit

- Projekt-Header: 4–6 Zeilen.
- Jeder Funktionsblock: 3–6 Zeilen Logikblock-Kommentar.
- Jede Variable: 3 Zeilen Kommentar (Zweck, Werte, Auswirkung).
- Jede Variable muss vollständig erklärt sein, keine unkommentierten Werte.
- Sprechende Schlüsselnamen, konsistente Einrückung, max. 80–100 Zeichen pro Zeile.

### B4 – Beispiel-Header

```yaml
# Projekt: Synology Photo Workflow
# Datei: config/config.explained.yaml
# Funktion: Erweiterte Erläuterung der aktuellen config.yaml mit denselben Werten.
# Hinweis: Diese Datei erklärt jede Variable explizit und beschreibt mögliche Werte und Auswirkungen.
```

### B5 – Beispiel-Logikblock

```yaml
# -----------------------------------------------------------------------------
# phase2
# Dieser Block steuert die Sicherheitsgrenze zwischen Archivierung und Löschung.
# Änderungen hier sind besonders sensibel, weil sie den Umgang mit ARW-Dateien beeinflussen.
# -----------------------------------------------------------------------------
phase2:
```

### B6 – Beispiel-Variable

```yaml
# delete_unneeded_arws_after_verified_archive: ARWs erst nach verifiziertem Archiv löschen.
# Mögliche Werte: true oder false.
# Auswirkung: true erlaubt die kontrollierte Bereinigung nach erfolgreicher Prüfung; false löst nichts aus.
delete_unneeded_arws_after_verified_archive: true
```

### B7 – Validierung und Abnahme

- Projekt-Header vorhanden?
- Logikblock vor jedem Funktionsblock vorhanden?
- Variablen-Kommentare mit Zweck, Werten und Auswirkung vorhanden?
- Alle möglichen Eingabewerte vollständig dokumentiert?
- Boolean-Semantik (true = aktiv, false = neutral) eingehalten?
- Konsistente Formatierung und Einrückung?

Bei Fehlern: Config ungültig markieren, loggen, manuelle Korrektur.

### B8 – Versionierung und Änderungshistorie

- Jede Config-Datei braucht Versionsnummer im Header.
- Jede Änderung muss im Header dokumentiert werden.
- Jede Änderung muss zusätzlich im CHANGELOG.md dokumentiert werden.

## Anhang C — README-Anforderungen für Ordner

### C1 Geltungsbereich

Gilt für alle README-Dateien im NAS-Workflow-Bereich:

- `PHOTO_WORKFLOW/README.md`
- `01_TEMP_SD/README.md`
- `02_TEMP_IMAGES/README.md`
- `03_TEMP_DONE/README.md`
- `04_TEMP_FINAL/README.md`
- `00_TEMP_ERROR/README.md`
- `MANUAL_KEEP/README.md`, `MANUAL_KEEP/inbox/README.md`, `MANUAL_KEEP/used/README.md`
- `WORKFLOW_DATA/README.md` und alle direkten Unterordner

### C2 Pflichtfelder pro README

1. Zweck
2. Eingaben
3. Prozess
4. Ausgaben
5. Manuelle Aktionen
6. Lebenszyklus
7. Fehlerfälle
8. Konfiguration (optional, falls relevant)

### C3 Format und Umfang

- Markdown, klare Überschriften, Aufzählungen mit Bindestrichen.
- Mindestens 100, maximal 500 Wörter.
- Deutsch, technisch präzise, frei von Floskeln.
- Mindestens ein konkretes Beispiel.
- Keine externen URLs.

### C4 Validierung

- Alle 8 Pflichtfelder vorhanden?
- Wortumfang eingehalten?
- Ein Beispiel enthalten?
- Keine externen URLs?
- Technische Korrektheit?

### C5 Versionierung

- README braucht Versionsnummer im Header.
- Änderungshistorie im CHANGELOG.md.
- Migration bei Struktur- oder Prozessänderung.

### C6 — Beispiel-README für TEMP_SD

```markdown
## TEMP_SD

### Zweck
Eingang für neue Kameraordner. Hier werden frische DCIM-Ordner (z. B. `100CANON`) abgelegt, bevor Phase 1 beginnt.

### Eingaben
- Nur frische Kameraordner
- Nur JPGs und ARWs im Originalzustand
- Abgelegt durch Mensch oder automatischen Import

### Prozess
Phase 1 liest von hier, normalisiert Datum, lagert ARWs aus, erzeugt Batch-Struktur und bewertet JPGs.

### Ausgaben
- Nach Phase 1: Batch wird nach `TEMP_IMAGES/` überführt.

### Manuelle Aktionen
- Neue Kameraordner ablegen (erlaubt)
- Bestehende Batches verändern (verboten)
- Dateien löschen (verboten)

### Lebenszyklus
Ein Batch gilt als abgeschlossen, wenn Phase 1 erfolgreich nach `TEMP_IMAGES/` verschoben wurde.

### Fehlerfälle
- Ungültiger Ordnername: Ignorieren, Log-Eintrag, manuelle Prüfung erforderlich.
- Fehlende ARWs: Der Batch wird nicht automatisch als Metadatenfehler behandelt. Die Zuordnung wird geprüft; bei widersprüchlicher Struktur greift `review_state_invalid`.
- Beschädigte JPGs: Phase 1 setzt `analysis_error`; der Batch oder das betroffene Artefakt wird nach dem Fehlervertrag behandelt.

### Konfiguration
- `paths.temp_sd`
- `workflow.batch_sort`
```

## Anhang D — Referenzpool-Feldreferenz

Die normative Referenzpool-Logik steht ausschließlich in Abschnitt 5.

### D1 – `selection.json`

Pflichtfelder:
- `schema_version`
- `pool_type`
- `slug` (nur Face)
- `updated_at`
- `selection_fingerprint`
- `pool_build_id`
- `rank_digits`
- `limits`
- `images`

### D2 – Bilddatensatz

Pflichtfelder:
- `source_id`
- `batch_id`
- `path` oder `crop_source`
- `status`: `active`, `new` oder `unknown`
- `quality_score`
- `pool_utility_score` oder `candidate_utility_score`
- `pool_rank` und `approved_at` nur bei `status: active`

Face-spezifische Felder: `bounding_box`, `face_confidence`, `original_path`.
Geschmacksspezifische Felder: `base_score`.

`unknown` ist ausschließlich für Recovery zulässig. Embeddings, Bildbytes und binäre Daten sind in `selection.json` verboten.

## Anhang E — Konsistenzprüfung und Recovery

### E1 — Konsistenzprüfung

- Dateiliste lesen.
- `selection.json` lesen.
- Vergleich: jeder Eintrag muss einer Datei entsprechen; jede Datei muss einem Eintrag entsprechen.
- Fehlende Dateien aus `selection.json` entfernen.
- Neue Dateien in `selection.json` aufnehmen.

### E2 — Recovery

- Fehlende Dateien: Eintrag aus `selection.json` entfernen und Änderung protokollieren.
- Neue nicht zuordenbare Dateien: Eintrag mit `status: unknown` aufnehmen; keine Scores vergeben; nicht für Matching oder Training verwenden; menschliche Prüfung verlangen.
- Änderung in `reference/`: Rebuild auslösen.
- Änderung in `reference/`: RAM-Embedding-Cache invalidieren.
- Änderung von Modell, Vorverarbeitung, Auswahlparametern, `selection_fingerprint` oder `pool_build_id`: Rebuild und Cache-Neuaufbau auslösen.
- Scheitert ein Rebuild: vorherige Poolversion aktiv lassen und Fehler in der Run-Summary melden.