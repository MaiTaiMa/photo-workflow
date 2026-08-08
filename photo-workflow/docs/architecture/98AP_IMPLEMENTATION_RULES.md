# 98AP – Implementierungsregeln (konsolidiert aus v1.1)

**Status:** Referenzdokument, kein eigenständiges Arbeitspaket  
**Abhängigkeiten:** Keine  
**Ziel:** Kompakte, mit Quellenkapiteln versehene Konsolidierung der in v1.1 verstreuten projektweiten Regeln und Datei-Kommentarpflichten, damit jedes AP nicht mehrere Spec-Kapitel parallel laden muss

## Kontext-Begrenzung

Dieses Dokument ersetzt **nicht** die Spezifikation. Es fasst nur bereits normative Inhalte zusammen und verweist auf die Quelle. Bei Detailfragen, die hier nicht beantwortet werden, ist ausschließlich das genannte Kapitel unter `docs/spec_v1-1/` zu konsultieren – niemals `docs/spec_v1-1/99_Basic-Photo-Workflow_Spezifikation_v1-1.md`.

## 1. AP-Zuordnungstabelle

Jedes AP muss ausschließlich die hier aufgeführten Abschnitte prüfen – nicht das gesamte Dokument. Abschnittsnummern beziehen sich auf dieses Dokument.

| AP-Datei | Betroffene Dateitypen | Relevante Abschnitte |
|---|---|---|
| 01AP.md | `.py` | 3, 6 |
| 02AP.md | `.py` | 3, 4 |
| 03AP.md | `.py` | 3, 4 |
| 04AP.md | `.py` | 3, 4 |
| 05AP.md | `.py` | 3, 5 |
| 06AP.md | `.py` | 3, 5, 7, 9 |
| 07AP.md | `.py` | 5 |
| 08AP.md | `.py` | 5 |
| 09AP.md | `.py` | 5 |
| 10AP.md | `.py` | 4 |
| 11AP.md | `.py` | 3, 4, 5 |
| 12AP.md | `.py` | 3, 4, 5 |
| 13AP.md | `.py` | 3, 6 |
| 14AP.md | `.sh`, `Dockerfile`, `.yml` | 3, 6, **8.1 (Skript-Header verbindlich)** |
| 15AP.md | `.py` | 3, 6 |
| 16AP.md | `.py` | 3 |
| 17AP.md | `.py` | 3, 4, 6 |
| 18AP.md | `.py` | 3, 6 |
| 19AP.md | `.py` | 3, 5 |
| 20AP.md | `.sh`, `.md` | 3, 4, 6, **8.1 (Skript-Header verbindlich)** |

Für alle mit `.py` gekennzeichneten APs gilt Abschnitt 8.1 (Skript-Anforderungen) ebenso verbindlich wie für `.sh`, siehe Abschnitt 2.

**Anmerkung zu Config- und JSON-Dateien:** Kein AP der aktuellen Liste erstellt oder ändert direkt `config.yaml` (nur `01AP.md` validiert sie). Sobald ein AP `config.yaml` erstellt oder ändert, greift zusätzlich Abschnitt 8.2. Für JSON-Artefakte (State, Manifest, ArchivePlan) gilt statt Kommentarpflicht Abschnitt 8.3.

## 2. Anwendungsbereich der Header- und Kommentarregeln

| Dateityp | Regelquelle | Status |
|---|---|---|
| `.py` und `.sh` (Skript-Dateien) | Anhang A, `07_Anhaenge.md` | v1.1-normativ. „Skript-Dateien" umfasst gleichrangig Python- und Bash-Skripte; beide unterliegen identisch den Struktur-, Kommentardichte- und Header-Anforderungen aus Anhang A. |
| `.yaml` (Config-Dateien) | Anhang B, `07_Anhaenge.md` | v1.1-normativ, unverändert übernommen; Kommentarpflicht gilt vollständig. |
| `.json` (State/Manifest/Archiv-Artefakte) | Abgeleitet aus den jeweiligen Datenverträgen in `00AP.md`/`02_...md` | JSON kennt syntaktisch keine Kommentare; Anhang B ist darauf technisch nicht anwendbar. Ersatz: verpflichtende Metadatenfelder (`schema_version`, `producer_version`, Zeitstempel, Hash), die bereits in den jeweiligen Datenverträgen vorgeschrieben sind. |

## 3. Projektweite Grundsätze

| Regel | Quelle |
|---|---|
| Abwägungslogik bei Zielkonflikten, verbindlich und vorrangig: 1. Sicherheit, 2. Stabilität, 3. Nutzen, 4. Einfachheit, 5. Performance. Gilt projektweit für Fachlogik, Architektur, Konfiguration, Betrieb und Tests. | `00_Geltungsbereich_und_Zielbild.md` 0.2.2 |
| Normative Schlüsselwörter `MUSS`, `DARF NICHT`, `SOLL`, `KANN` sind verbindlich auszulegen. | `00_...md` 0.2.1 |
| Geschützte Bilddaten, Face-Crops, Embeddings und Referenzbilder verlassen nie die erlaubten NAS-Datenbereiche. | `00_...md` 0.2.2, 1.2 |
| Original-JPGs und ARWs dürfen weder still überschrieben noch gelöscht werden. | `00_...md` 1.1 |
| Automatisch erzeugte Face-Crops nur in `WORKFLOW_DATA/faces/<slug>/new_faces/`; Aktivierung nach `reference/` ausschließlich manuell durch den Menschen. | `00_...md` 1.2 |
| Bildbytes und Embeddings dürfen nie in JSON, Cache, Log, Manifest, CSV, Report, eingebetteten Metadaten oder API-Aufrufen persistiert werden; Embeddings nur RAM-flüchtig während des aktiven Container-Laufs. | `00_...md` 1.2 |
| Alle produktiven Pfade müssen innerhalb von `paths.basedir` liegen; kanonische Pfadprüfung blockiert `..`-Traversal, unerlaubte Symlinks und Mountwechsel. | `00_...md` 1.3 |
| `config.yaml` bleibt secrets-frei; API-Credentials und Session-Token ausschließlich über Container-Umgebungsvariablen, nie in Dateien, Batch-Manifests, CSVs, Logs, Reports oder Run-Summaries. | `00_...md` 1.3 |
| API-Fehler dürfen niemals Löschung, Überschreiben, Rücktransfer oder eine sonstige unkontrollierte Dateiänderung auslösen. | `00_...md` 1.3 |

## 4. Batch-, State- und Archivregeln

| Regel | Quelle |
|---|---|
| Keine ARW-Aktion ohne vollständig verifiziertes und aktiviertes JPG- und ARW-Archiv; bei Fehler bleibt das ARW erhalten. | `02_Batch_Phasen_und_Recovery.md` |
| Atomarität: Inhalt erzeugen, validieren, temporär auf gleichem Dateisystem schreiben, erneut validieren, atomar ersetzen; vorherige gültige Version bleibt bis zur Aktivierung erhalten. | `02_...md` |
| Jeder Zustandsübergang wird atomar mit Zeitstempel und Hash protokolliert; Rückwärts-Übergänge nur bei Quarantäne. | `02_...md` |
| Globaler Lock verhindert parallele produktive Läufe. | `02_...md` |
| `review_state_invalid` blockiert jede ARW-Aktion vollständig; Batch wird nach `00_TEMP_ERROR` verschoben. | `02_...md` |
| ZIP-Archive: Lesbarkeit, Traversal, Größenlimit, Kompressionsverhältnis prüfen; Kollisionen erzeugen neuen Namen, nie Überschreibung; Hash vor/nach Aktivierung prüfen. | `02_...md` |

## 5. Scoring- und Metadatenregeln

| Regel | Quelle |
|---|---|
| Nicht lesbare oder fehlerhafte Bilder erhalten `analysis_error`, nie einen stillen Ersatzscore. | `03_Scoring_Metadaten_und_Faces.md` |
| `base_score`/`personal_score`/`eye_score`/`family_score` sind Fließkommazahlen [0,0–1,0] oder `None`; `analysis_error` nie als `0.0`. | `03_...md` |
| Manual Keep erzwingt `keep` mit Grund `manual_keep_match`; Quelldatei wird erst nach Zuordnung nach `used/` verschoben. | `03_...md` |
| Metadaten müssen namespaced sein (`workflow:`, `decision:`, `series:`, `family:`, `person:`, `manual_keep:`); Schreiben per `exiftool` mit `shell=False`; nach dem Schreiben zurücklesen und abgleichen. | `03_...md` |

## 6. Betrieb und Konfiguration

| Regel | Quelle |
|---|---|
| Config-Schema: YAML mit strikter Validierung; unbekannte Schlüssel sind Fehler außer `extensions`; Config-Schlüssel durchgängig `snake_case`. | `05_Betrieb_Konfiguration.md` |
| Effektive Konfiguration wird mit SHA256-Fingerprint im Run dokumentiert. | `05_...md` |
| Not-Stop bei Zeitbudget/SIGTERM: keinen neuen teuren Schritt beginnen, aktuellen Schritt sicher abschließen, Status `paused` atomar schreiben. | `05_...md` |

## 7. Referenzpool-Regeln

| Regel | Quelle |
|---|---|
| Kapazitätsgrenzen `max_active`, `max_new`, `max_new_per_batch` sind Hard Limits; `min_active` ist Soft Limit und pausiert nur den betroffenen Adapter. | `04_Referenzpools_und_Rebuild.md` |
| `selection.json` ist die einzige Wahrheit je Pool; Embeddings, Bildbytes und binäre Daten sind darin verboten. | `04_...md` |
| Referenzpooländerung invalidiert den RAM-Embedding-Cache und löst einen Rebuild aus; scheitert der Rebuild, bleibt die vorherige Poolversion aktiv. | `04_...md` |

## 8. Datei-Header- und Kommentarpflichten

### 8.1 Skript-Dateien: Python und Bash (v1.1-normativ)

Quelle: `07_Anhaenge.md`, Anhang A. Der Begriff „Skript-Dateien" umfasst gleichrangig Python- (`.py`) und Bash-Dateien (`.sh`); beide Sprachen unterliegen identisch den folgenden Anforderungen.

- Geltungsbereich: alle Skript-Dateien im Repository, unabhängig von Python oder Bash.
- Feste Struktur: Header-Kommentar (6–10 Zeilen), Abschnitts-Kommentare (2–3 Zeilen je Abschnitt), Funktions-Kommentare (3–5 Zeilen je Funktion), Einzeiler bei komplexen Bedingungen.
- Ca. 20 % Kommentaranteil, sprechende Namen, konsistente Formatierung, max. 80–100 Zeichen pro Zeile.
- Header-Beispiel (Bash):

```bash
#!/bin/bash
#
# Skript: scripts/<name>.sh
# Zweck: <eine Zeile Zweckbeschreibung>
# Autor: <Name>
# Erstellt: <Datum>
# Version: <Versionsnummer>
# Requires: <Abhängigkeiten>
# Usage: <Aufrufbeispiel>
#
# Änderungsprotokoll:
#   <Datum> | <Version> | <Änderung>
#
```

- Header-Beispiel (Python), identisches Schema:

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

- Jede Skript-Datei (Python oder Bash) braucht eine Versionsnummer im Header; jede Änderung wird im Header **und** zusätzlich in `CHANGELOG.md` dokumentiert.
- Abnahme: Header-, Abschnitts- und Funktionskommentare vorhanden, ca. 20 % Kommentaranteil, sprechende Namen, konsistente Formatierung; bei Fehlern gilt die Datei als ungültig und erfordert manuelle Korrektur.

### 8.2 Config-Dateien (`.yaml`, v1.1-normativ)

Quelle: `07_Anhaenge.md`, Anhang B. Relevant für jedes AP, das `config.yaml` oder Varianten wie `config.explained.yaml` erstellt oder ändert. Die Kommentarpflicht gilt vollständig und ohne Ausnahme.

- Feste Struktur: Projekt-Header (4–6 Zeilen, einmalig), Logikblock-Kommentar vor jedem Funktionsblock (3–6 Zeilen mit Trennlinien), Variablen-Kommentar (3 Zeilen: Zweck, Mögliche Werte, Auswirkung), Zusatzzeilen (`Voraussetzung:`, `Hinweis:`) bei komplexen Variablen.
- Jede Variable muss vollständig erklärt sein; keine unkommentierten Werte; sprechende Schlüsselnamen; max. 80–100 Zeichen pro Zeile.
- Boolean-Semantik verbindlich: `true` aktiviert/löst die beschriebene Funktion aus, `false` ist der neutrale Zustand und löst nichts aus; dies muss in der Auswirkungszeile explizit stehen.
- Beispiel-Header:

```yaml
# Projekt: Synology Photo Workflow
# Datei: config/config.yaml
# Funktion: Zentrale Konfiguration des Photo Workflow.
# Hinweis: Jede Variable ist unten mit Zweck, möglichen Werten und Auswirkung erklärt.
```

- Beispiel-Logikblock:

```yaml
# -----------------------------------------------------------------------------
# phase2
# Dieser Block steuert die Sicherheitsgrenze zwischen Archivierung und Löschung.
# Änderungen hier sind besonders sensibel, weil sie den Umgang mit ARW-Dateien beeinflussen.
# -----------------------------------------------------------------------------
phase2:
```

- Beispiel-Variable:

```yaml
# <schluessel>: <eine Zeile Zweckbeschreibung>
# Mögliche Werte: <vollständige Aufzählung erlaubter Eingaben>
# Auswirkung: <was true/false konkret auslöst oder verhindert>
<schluessel>: <wert>
```

- Jede Config-Datei braucht eine Versionsnummer im Header; jede Änderung wird im Header **und** zusätzlich in `CHANGELOG.md` dokumentiert.
- Abnahme: Projekt-Header, Logikblöcke, vollständige Variablen-Kommentare, eingehaltene Boolean-Semantik, konsistente Formatierung; bei Fehlern gilt die Config als ungültig und erfordert manuelle Korrektur.

### 8.3 JSON-Artefakte (State, Manifest, ArchivePlan, Review-Record)

JSON unterstützt keine Kommentare; Anhang B ist darauf technisch nicht übertragbar. Stattdessen gilt der bereits in den jeweiligen Datenverträgen (siehe `00AP.md` Abschnitt 4, `02_...md`) festgelegte Pflichtfeldsatz als Ersatz für den Header:

- Pflichtfelder je Artefakt: `schema_version`, `producer_version`, Zeitstempel (`created_at`/`updated_at`/`timestamp`), `hash` bzw. `config_fingerprint`, sofern im jeweiligen Vertrag definiert.
- Diese Felder sind keine neue Regel, sondern die konsequente Anwendung der bereits bestehenden Artefaktverträge; sie ersetzen für JSON den Kommentar-Header.

### 8.4 README-Dateien für NAS-Ordner (Anhang C, nur bei Bezug relevant)

- Pflichtfelder: Zweck, Eingaben, Prozess, Ausgaben, Manuelle Aktionen, Lebenszyklus, Fehlerfälle, optional Konfiguration.
- Markdown, 100–500 Wörter, Deutsch, technisch präzise, mindestens ein konkretes Beispiel, keine externen URLs.
- Versionsnummer im Header, Änderungshistorie in `CHANGELOG.md`, Migration bei Struktur-/Prozessänderung.

## 9. Referenzpool-Feldreferenz und Recovery (Anhang D/E, nur bei Bezug relevant)

- `selection.json`-Pflichtfelder: `schema_version`, `pool_type`, `slug` (nur Face), `updated_at`, `selection_fingerprint`, `pool_build_id`, `rank_digits`, `limits`, `images`.
- Bilddatensatz-Pflichtfelder: `source_id`, `batch_id`, `path`/`crop_source`, `status` (`active`/`new`/`unknown`), `quality_score`, `pool_utility_score`/`candidate_utility_score`; `pool_rank`/`approved_at` nur bei `status: active`.
- `unknown` ist ausschließlich für Recovery zulässig, nie für Matching oder Training.
- Konsistenzprüfung: Dateiliste und `selection.json` müssen deckungsgleich sein; Abweichungen werden protokolliert und ausgeglichen.

## 10. Geltung für alle Arbeitspakete

Jedes AP prüft ausschließlich die in der Zuordnungstabelle (Abschnitt 1) genannten Abschnitte. Eine vollständige Prüfung des gesamten Dokuments ist nicht vorgesehen und nicht erforderlich.
