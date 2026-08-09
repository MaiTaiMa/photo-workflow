# Coding Style & Datei-Kommentarregeln

**Status:** Referenzdokument, kein eigenständiges Arbeitspaket  
**Abhängigkeiten:** Keine  
**Ziel:** Skripte mit einem Qualitätsstandard für Kommentare und Header zu versehen

## 1. Anwendungsbereich

| Dateityp | Regelquelle | Status |
|---|---|---|
| `.py` und `.sh` (Skript-Dateien) | Anhang A | Verbindlich. Python- und Bash-Skripte unterliegen identisch den Struktur-, Kommentardichte- und Header-Anforderungen. |
| `.yaml` (Config-Dateien) | Anhang B | Verbindlich. Kommentarpflicht gilt vollständig für alle Variablen. |
| `.json` (State/Manifest/Archiv-Artefakte) | Abschnitt 4 | JSON kennt keine Kommentare. Ersatz: Pflicht-Metadatenfelder in jedem Artefakt. |

---

## 2. Projektweite Grundsätze

- **Abwägungslogik bei Zielkonflikten** (verbindlich): 1. Sicherheit, 2. Stabilität, 3. Nutzen, 4. Einfachheit, 5. Performance.
- **Normative Schlüsselwörter** `MUSS`, `DARF NICHT`, `SOLL`, `KANN` sind verbindlich auszulegen.
- **Sprechende Namen** für Variablen, Funktionen, Klassen und Konfigurationsschlüssel.
- **Konsistente Formatierung** im gesamten Repository.
- **Max. 80–100 Zeichen** pro Zeile.

---

## 3. Skript-Dateien (Python & Bash)

### 3.1 Header-Kommentar (verbindlich)

Jede `.py`- und `.sh`-Datei benötigt einen Header mit 6–10 Zeilen:

```python
"""
Skript: app/<name>.py
Zweck: <eine Zeile Zweckbeschreibung>
Autor: <Name>
Erstellt: <Datum>
Version: <Versionsnummer>
Requires: <Abhängigkeiten>

Änderungsprotokoll:
  <Datum> | <Version> | <Änderung>
"""
```

```bash
#!/bin/bash
# Skript: scripts/<name>.sh
# Zweck: <eine Zeile Zweckbeschreibung>
# Autor: <Name>
# Erstellt: <Datum>
# Version: <Versionsnummer>
# Requires: <Abhängigkeiten>
# Usage: <Aufrufbeispiel>
# Änderungsprotokoll:
#   <Datum> | <Version> | <Änderung>
#
```

### 3.2 Kommentaranteil

- **Ca. 20 %** Kommentaranteil im gesamten Skript.
- **Abschnitts-Kommentare:** 2–3 Zeilen je Abschnitt mit Trennlinien.
- **Funktions-Kommentare:** 3–5 Zeilen je Funktion.
- **Einzeiler** bei komplexen Bedingungen.

### 3.3 Versionsverwaltung

- Jede Skript-Datei braucht eine **Versionsnummer im Header**.
- Jede Änderung wird im Header **und** zusätzlich in `CHANGELOG.md` dokumentiert.

---

## 4. Config-Dateien (`.yaml`)

### 4.1 Projekt-Header (einmalig)

```yaml
# Projekt: Synology Photo Workflow
# Datei: config/config.yaml
# Funktion: Zentrale Konfiguration des Photo Workflow.
# Hinweis: Jede Variable ist unten mit Zweck, möglichen Werten und Auswirkung erklärt.
```

### 4.2 Logikblock-Kommentar (vor jedem Block)

```yaml
# -----------------------------------------------------------------------------
# phase2
# Dieser Block steuert die Sicherheitsgrenze zwischen Archivierung und Löschung.
# Änderungen hier sind besonders sensibel, weil sie den Umgang mit ARW-Dateien beeinflussen.
# -----------------------------------------------------------------------------
phase2:
```

### 4.3 Variablen-Kommentar (verbindlich)

Jede Variable MUSS vollständig erklärt sein:

```yaml
# <schluessel>: <eine Zeile Zweckbeschreibung>
# Mögliche Werte: <vollständige Aufzählung erlaubter Eingaben>
# Auswirkung: <was true/false konkret auslöst oder verhindert>
<schluessel>: <wert>
```

### 4.4 Boolean-Semantik

- `true` aktiviert/löst die beschriebene Funktion aus.
- `false` ist der neutrale Zustand und löst nichts aus.
- Dies MUSS in der Auswirkungszeile explizit stehen.

### 4.5 Versionsverwaltung

- Jede Config-Datei braucht eine **Versionsnummer im Header**.
- Jede Änderung wird im Header **und** zusätzlich in `CHANGELOG.md` dokumentiert.

---

## 5. JSON-Artefakte (State, Manifest, ArchivePlan)

JSON unterstützt keine Kommentare. Stattdessen gelten folgende **Pflicht-Metadatenfelder** in jedem Artefakt:

- `schema_version` – Version des Daten-Schemas
- `producer_version` – Version des erzeugenden Skripts
- Zeitstempel (`created_at`, `updated_at`, oder `timestamp`)
- `hash` oder `config_fingerprint` – Integritätsprüfung

Diese Felder ersetzen für JSON den Kommentar-Header.

---

## 6. Abnahme-Kriterien

Bei jeder Änderung MUSS folgendes geprüft werden:

- [ ] Header vorhanden (Skript/Config)
- [ ] Abschnitts-Kommentare vorhanden (Skript)
- [ ] Funktions-Kommentare vorhanden (Skript)
- [ ] Alle Variablen kommentiert (Config)
- [ ] Ca. 20 % Kommentaranteil (Skript)
- [ ] Sprechende Namen verwendet
- [ ] Konsistente Formatierung eingehalten
- [ ] Max. 80–100 Zeichen pro Zeile
- [ ] Versionsnummer im Header aktualisiert
- [ ] Änderung in `CHANGELOG.md` dokumentiert

**Bei Fehlern gilt die Datei als ungültig und erfordert manuelle Korrektur.**