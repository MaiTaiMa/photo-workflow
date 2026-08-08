# 98AP – Implementierungsregeln (konsolidiert aus v1.1)

**Status:** Referenzdokument, kein eigenständiges Arbeitspaket  
**Abhängigkeiten:** Keine  
**Ziel:** Kompakte, mit Quellenkapiteln versehene Konsolidierung der in v1.1 verstreuten projektweiten Regeln und Datei-Kommentarpflichten, damit jedes AP nicht mehrere Spec-Kapitel parallel laden muss

## Kontext-Begrenzung

Dieses Dokument ersetzt **nicht** die Spezifikation. Es fasst nur bereits normative Inhalte zusammen und verweist auf die Quelle. Bei Detailfragen, die hier nicht beantwortet werden, ist ausschließlich das genannte Kapitel unter `docs/spec_v1-1/` zu konsultieren – niemals `docs/spec_v1-1/99_Basic-Photo-Workflow_Spezifikation_v1-1.md`.

## 1. Projektweite Grundsätze

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

## 2. Batch-, State- und Archivregeln

| Regel | Quelle |
|---|---|
| Keine ARW-Aktion ohne vollständig verifiziertes und aktiviertes JPG- und ARW-Archiv; bei Fehler bleibt das ARW erhalten. | `02_Batch_Phasen_und_Recovery.md` |
| Atomarität: Inhalt erzeugen, validieren, temporär auf gleichem Dateisystem schreiben, erneut validieren, atomar ersetzen; vorherige gültige Version bleibt bis zur Aktivierung erhalten. | `02_...md` |
| Jeder Zustandsübergang wird atomar mit Zeitstempel und Hash protokolliert; Rückwärts-Übergänge nur bei Quarantäne. | `02_...md` |
| Globaler Lock verhindert parallele produktive Läufe. | `02_...md` |
| `review_state_invalid` blockiert jede ARW-Aktion vollständig; Batch wird nach `00_TEMP_ERROR` verschoben. | `02_...md` |
| ZIP-Archive: Lesbarkeit, Traversal, Größenlimit, Kompressionsverhältnis prüfen; Kollisionen erzeugen neuen Namen, nie Überschreibung; Hash vor/nach Aktivierung prüfen. | `02_...md` |

## 3. Scoring- und Metadatenregeln

| Regel | Quelle |
|---|---|
| Nicht lesbare oder fehlerhafte Bilder erhalten `analysis_error`, nie einen stillen Ersatzscore. | `03_Scoring_Metadaten_und_Faces.md` |
| `base_score`/`personal_score`/`eye_score`/`family_score` sind Fließkommazahlen [0,0–1,0] oder `None`; `analysis_error` nie als `0.0`. | `03_...md` |
| Manual Keep erzwingt `keep` mit Grund `manual_keep_match`; Quelldatei wird erst nach Zuordnung nach `used/` verschoben. | `03_...md` |
| Metadaten müssen namespaced sein (`workflow:`, `decision:`, `series:`, `family:`, `person:`, `manual_keep:`); Schreiben per `exiftool` mit `shell=False`; nach dem Schreiben zurücklesen und abgleichen. | `03_...md` |

## 4. Referenzpool-Regeln

| Regel | Quelle |
|---|---|
| Kapazitätsgrenzen `max_active`, `max_new`, `max_new_per_batch` sind Hard Limits; `min_active` ist Soft Limit und pausiert nur den betroffenen Adapter. | `04_Referenzpools_und_Rebuild.md` |
| `selection.json` ist die einzige Wahrheit je Pool; Embeddings, Bildbytes und binäre Daten sind darin verboten. | `04_...md` |
| Referenzpooländerung invalidiert den RAM-Embedding-Cache und löst einen Rebuild aus; scheitert der Rebuild, bleibt die vorherige Poolversion aktiv. | `04_...md` |

## 5. Betrieb und Konfiguration

| Regel | Quelle |
|---|---|
| Config-Schema: YAML mit strikter Validierung; unbekannte Schlüssel sind Fehler außer `extensions`; Config-Schlüssel durchgängig `snake_case`. | `05_Betrieb_Konfiguration.md` |
| Effektive Konfiguration wird mit SHA256-Fingerprint im Run dokumentiert. | `05_...md` |
| Not-Stop bei Zeitbudget/SIGTERM: keinen neuen teuren Schritt beginnen, aktuellen Schritt sicher abschließen, Status `paused` atomar schreiben. | `05_...md` |

## 6. Datei-Header- und Kommentarpflichten

Diese Pflichten gelten für **jede vom Projekt erstellte oder geänderte** Skript- bzw. Config-Datei. Quelle: `07_Anhaenge.md`, Anhang A und B.

### 6.1 Skript-Dateien (Anhang A)

- Geltungsbereich: alle Skript-Dateien im Repository.
- Feste Struktur: Header-Kommentar (6–10 Zeilen), Abschnitts-Kommentare (2–3 Zeilen je Abschnitt), Funktions-Kommentare (3–5 Zeilen je Funktion), Einzeiler bei komplexen Bedingungen.
- Ca. 20 % Kommentaranteil, sprechende Namen, konsistente Formatierung, max. 80–100 Zeichen pro Zeile.
- Header-Beispiel:

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

- Jede Skript-Datei braucht eine Versionsnummer im Header; jede Änderung wird im Header **und** zusätzlich in `CHANGELOG.md` dokumentiert.
- Abnahme: Header-, Abschnitts- und Funktionskommentare vorhanden, ca. 20 % Kommentaranteil, sprechende Namen, konsistente Formatierung; bei Fehlern gilt das Skript als ungültig und erfordert manuelle Korrektur.

### 6.2 Config-Dateien (Anhang B)

- Geltungsbereich: alle Config-Dateien im Repository, einschließlich erklärter Varianten wie `config.explained.yaml`.
- Feste Struktur: Projekt-Header (4–6 Zeilen, einmalig), Logikblock-Kommentar vor jedem Funktionsblock (3–6 Zeilen mit Trennlinien), Variablen-Kommentar (3 Zeilen: Zweck, Mögliche Werte, Auswirkung), Zusatzzeilen (`Voraussetzung:`, `Hinweis:`) bei komplexen Variablen.
- Jede Variable muss vollständig erklärt sein; keine unkommentierten Werte; sprechende Schlüsselnamen; max. 80–100 Zeichen pro Zeile.
- Boolean-Semantik verbindlich: `true` aktiviert/löst die beschriebene Funktion aus, `false` ist der neutrale Zustand und löst nichts aus; dies muss in der Auswirkungszeile explizit stehen.
- Beispiel-Variable:

```yaml
# <schluessel>: <eine Zeile Zweckbeschreibung>
# Mögliche Werte: <vollständige Aufzählung erlaubter Eingaben>
# Auswirkung: <was true/false konkret auslöst oder verhindert>
<schluessel>: <wert>
```

- Jede Config-Datei braucht eine Versionsnummer im Header; jede Änderung wird im Header **und** zusätzlich in `CHANGELOG.md` dokumentiert.
- Abnahme: Projekt-Header, Logikblöcke, vollständige Variablen-Kommentare, eingehaltene Boolean-Semantik, konsistente Formatierung; bei Fehlern gilt die Config als ungültig und erfordert manuelle Korrektur.

### 6.3 README-Dateien für NAS-Ordner (Anhang C, sofern ein AP READMEs erstellt)

- Pflichtfelder: Zweck, Eingaben, Prozess, Ausgaben, Manuelle Aktionen, Lebenszyklus, Fehlerfälle, optional Konfiguration.
- Markdown, 100–500 Wörter, Deutsch, technisch präzise, mindestens ein konkretes Beispiel, keine externen URLs.
- Versionsnummer im Header, Änderungshistorie in `CHANGELOG.md`, Migration bei Struktur-/Prozessänderung.

## 7. Referenzpool-Feldreferenz und Recovery (Anhang D/E, nur bei Bezug relevant)

- `selection.json`-Pflichtfelder: `schema_version`, `pool_type`, `slug` (nur Face), `updated_at`, `selection_fingerprint`, `pool_build_id`, `rank_digits`, `limits`, `images`.
- Bilddatensatz-Pflichtfelder: `source_id`, `batch_id`, `path`/`crop_source`, `status` (`active`/`new`/`unknown`), `quality_score`, `pool_utility_score`/`candidate_utility_score`; `pool_rank`/`approved_at` nur bei `status: active`.
- `unknown` ist ausschließlich für Recovery zulässig, nie für Matching oder Training.
- Konsistenzprüfung: Dateiliste und `selection.json` müssen deckungsgleich sein; Abweichungen werden protokolliert und ausgeglichen.

## 8. Geltung für alle Arbeitspakete

Jedes AP muss in seinem Abschnitt „Relevante Regeln aus v1.1" nur die für seine Dateien zutreffenden Zeilen aus diesem Dokument zitieren oder referenzieren – keine vollständige Wiederholung. Bei jeder neu erstellten oder geänderten Skript- oder Config-Datei sind zusätzlich unverändert die Header- und Kommentarpflichten aus Abschnitt 6 einzuhalten.

---

**Hinweis zur Konsistenzprüfung:** Dieses Dokument wurde gegen die tatsächlichen Kapitel `00_Geltungsbereich_und_Zielbild.md` und `07_Anhaenge.md` abgeglichen. Eine Abweichung wurde korrigiert: Die Pflicht zum Config-Fingerprint gilt nicht allgemein „überall", sondern konkret für Manifeste, CSVs, Logs, Reports und Run-Summaries; API-Credentials sind davon ausdrücklich ausgeschlossen und dürfen dort nie erscheinen (siehe Abschnitt 1 dieses Dokuments).