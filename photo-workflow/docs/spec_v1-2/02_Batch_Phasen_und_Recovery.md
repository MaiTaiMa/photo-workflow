# 3. Batch-, Phasen- und Recovery-Vertrag

## 3.1 Batch-ID und Zustandsdatei

Die unveränderliche `batch_id` lautet `source-folder-name+fingerprint(8)` und bleibt beim Wechsel zwischen allen Arbeitsordnern gleich. Pro Batch gibt es genau eine zentrale Zustandsdatei `WORKFLOW_DATA/runtime/state/{batch_id}.json`; globale Zustandsdateien sind unzulässig.

**Batch-ID-Bildung:** Die `batch_id` wird bei Erstkontakt mit dem Batch aus dem Ordnernamen und einem 8-stelligen Fingerprint (SHA256, gekürzt) gebildet. Sie bleibt über alle Ordnerwechsel hinweg unverändert.

**Beispiel:** Ein Ordner `2024-08-15_Geburtstag` erhält die `batch_id` `2024-08-15_Geburtstag+a3f7c2e1`.

## 3.2 PHASE1 Aufbereitung, Bewertung und Ablage

- **Status:** Pflicht.
- **Zweck:** Phase 1 analysiert einen neuen Kamera-Batch, bewertet die Bilder und bereitet die menschliche Prüfung vor. Sie trennt ARWs von JPGs, normalisiert Datum und Namen, wendet Scoring, Serienlogik und Manual Keep an, schreibt Metadaten, CSV und das Phase-1-Manifest und übergibt den Batch erst nach vollständiger, sichtbarer Ablage atomar nach `02_TEMP_IMAGES`.

### Ablauf

1. Stabilitäts-, Namens-, Lock- und Symlink-Prüfung. Der Batch muss größen- und hashstabil sein; aktive Locks oder unsichere Symlinks blockieren die Verarbeitung.
2. Datumsnormalisierung. Aufnahmedaten werden aus Metadaten ermittelt, konsistent normalisiert und in Dateinamen und Batch-Metadaten übernommen.
3. ARW-Ablage nach `ARW`. Alle ARW-Dateien werden vollständig und hashgeprüft in den Unterordner `ARW` verschoben; die Zuordnung zu ihren JPGs wird dokumentiert.
4. Validiertes JPG-Archiv. JPGs werden auf Lesbarkeit, Integrität und Dekodierbarkeit geprüft; fehlerhafte Dateien werden als Analysefehler gemeldet. Eine Bewertung oder Endentscheidung ohne sichtbar dokumentierten Fehlerstatus ist stilles Scoring und darf nicht stattfinden.
5. Feature- und Score-Ermittlung einschließlich Manual Keep und Serienlogik. Pro JPG werden technische Scores, persönlicher Geschmack, Eye-Score und Family-Score berechnet. Serienlogik gruppiert ähnliche Bilder, Manual Keep erzwingt `keep` für erfolgreich zugeordnete extern ausgewählte Bilder.
6. Eingebettete Metadaten, CSV und Phase-1-Manifest. Ratings, Tags und Status werden in die Bilder geschrieben, anschließend rückgelesen und geprüft; zusätzlich entsteht `SAVE/culling_scores.csv` und ein JSON-Manifest mit Dateiliste, Countern, Hashes und Phase-1-Status.
7. Sichtbare Ablage in Hauptordner, `Review` oder `Rejected`. Jedes Bild wird entsprechend seiner Endentscheidung im Batch-Hauptordner, in `Review` oder in `Rejected` abgelegt; nur JPGs im Hauptordner gelten als aktiv und schützen ihr ARW.
8. Atomare Übergabe nach `02_TEMP_IMAGES` mit datum-basiertem Merge. Erst nach vollständiger und konsistenter Ablage wird der Batch atomar nach `02_TEMP_IMAGES` übergeben.

   **Merge-Logik (datum-basiert, Standard):**
   
   - Nach der Datumsnormalisierung (z. B. `33351102` → `2025-11-02`) wird der Zielordner anhand des Datumsprefixes gesucht.
   - Existiert bereits ein Ordner mit gleichem Datumsprefix und Suffix (z. B. `2025-11-02_Pause`), wird dorthin gemerged (Suffix hat Priorität!).
   - Existiert sowohl `2025-11-02` als auch `2025-11-02_Pause`, wird nach `2025-11-02_Pause` gemerged.
   - Existiert nur `2025-11-02`, wird dorthin gemerged.
   - Existiert kein passender Ordner, wird `2025-11-02` neu angelegt.
   
   **Beispiel:**
   

33351102 (wird zu 2025-11-02) + 02_TEMP_IMAGES/2025-11-02_Pause existiert
→ Merge nach 02_TEMP_IMAGES/2025-11-02_Pause (Suffix-Priorität)

Der Zustand `phase1_completed` wird erst nach erfolgreichem Merge geschrieben.

### PHASE1-Vertrag

- Phase 1 muss genau einen zentralen Zustandsrecord pro `batch_id` in `WORKFLOW_DATA/runtime/state/{batch_id}.json` führen.
- Jeder Zustandsrecord muss mindestens `state`, `timestamp`, `hash` (SHA256 des vorherigen Zustands) und `producer_version` enthalten; `reason` ist optional bei Fehler oder Quarantäne.
- Phase-1-Ergebnisse müssen mindestens `batch_id`, Pfade, Bildzähler, ARW-Zähler, Hash des `culling_scores.csv`, einen `manifest_hash` und den aktuellen Phase-/Review-/Kalibrierungsstatus enthalten.
- Das CSV muss pro Bild Scores, Serienmerkmale, Family-Match, Manual-Keep-Status und Metadatenstatus enthalten.
- Die sichtbare Ablage muss im Batch-Unterordner die kanonischen Ordner `ARW`, `SAVE`, `Review` und `Rejected` verwenden; sie darf keine ARWs still überschreiben oder löschen.

### PHASE1-Zustandsautomat

```text
phase1_started → phase1_moving → phase1_completed
```

- `phase1_started` dokumentiert den Beginn der Phase-1-Verarbeitung für einen neu erkannten Batch.
- `phase1_moving` dokumentiert, dass die sichtbare Batch-Übergabe begonnen hat. Der Zustand wird vor dem sichtbaren Dateimove atomar geschrieben.
- `phase1_completed` dokumentiert, dass alle acht Schritte der Phase 1 erfolgreich abgeschlossen und die Ergebnisse atomar nach `02_TEMP_IMAGES` übergeben wurden.

Zwischenzustand und Fehlerdetails werden über die allgemeine Zustandsdatei und Quarantäne abgebildet. Rückwärts-Übergänge sind nur bei Quarantäne zulässig.

**Beispiel:**

Ein Ordner `2024-08-15_Geburtstag` wird nach `01_TEMP_SD` kopiert und erhält die `batch_id` `2024-08-15_Geburtstag+a3f7c2e1`. Phase 1 prüft Stabilität und Symlinks, normalisiert Datum und Namen, lagert alle ARWs nach `ARW` aus, berechnet Scoring, Serien und Manual Keep, schreibt Metadaten und Manifest und legt die Bilder in Hauptordner, `Review` und `Rejected` ab. Anschließend wird der Batch atomar nach `02_TEMP_IMAGES` verschoben und der Zustand `phase1_completed` geschrieben.

## 3.3 PHASE2 Archivierung und ARW-Bereinigung

- **Status:** Pflicht für freigegebene Batches.
- **Zweck:** Phase 2 archiviert einen nach Phase 1 fertig sortierten und vom Menschen gesichteten Batch und bereinigt kontrolliert die ARW-Dateien. Sie muss zuerst Phase-1-Manifest und Endentscheidungen validieren, bei manueller Freigabe einen unveränderlichen Review-Record schreiben und erst danach archivieren. Ein ARW darf nur gelöscht werden, nachdem ein vollständiges Archiv erzeugt, geprüft, auf demselben Dateisystem atomar aktiviert und mit Hash protokolliert wurde. Bei jedem Fehler bleibt das ARW erhalten.

### Ablauf

1. Phase-2-Start. Phase 2 beginnt erst nach manueller Freigabe durch Move des gesamten Batches nach `03_TEMP_DONE` oder nach explizit zugelassener automatischer Übergabe (`automatic_handoff`).

**Automationsmodi für Phase 2:**

| Modus | Phase-2-Start | Move nach `04_TEMP_FINAL` |
|---|---|---|
| `auto_phase2` | nur bei `automatic_handoff` + allen Gates | **nicht erlaubt** |
| `full_auto` | nur bei `automatic_handoff` + allen Gates | erlaubt (zusätzlich `phase2.move_to_temp_final: true`) |

Die automatische Übergabe ist nur zulässig, wenn `phase2.automatic_handoff.enabled: true` gesetzt ist. Zusätzlich dürfen keine JPGs in `Review` liegen und kein Bild darf `analysis_error` tragen. Bei deaktiviertem Flag ist ausschließlich die manuelle Freigabe durch Verschieben des vollständigen Batches nach `03_TEMP_DONE` zulässig.
2. Validierung von Phase-1-Manifest und Endentscheidungen. Das Phase-1-Manifest, die sichtbare Ordnerstruktur und die Zuordnung ARW↔JPG werden geprüft.
3. Blockierender Zustand `review_state_invalid`. Mehrdeutige Paarungen, mehrere wirksame JPG-Kopien, fehlende Quellhashes oder widersprüchliche Ordnerzustände setzen `review_state_invalid`; der Batch wird nach `00_TEMP_ERROR` verschoben und als `blocking` gemeldet. Es darf keine ARW-Aktion stattfinden.
4. Review-Record und Kalibrierungsindex (manuelle Freigabe). Bei manueller Freigabe muss zuerst ein unveränderlicher Review-Record mit menschlicher Endentscheidung geschrieben werden, danach ein Kalibrierungsindex für den Gewichtungsassistenten.
5. Archivierung. Phase 2 erzeugt ein Archiv gemäß Archivvertrag, prüft es vollständig per Dateiliste, Größe und SHA256, behandelt Namenskollisionen durch neue Archivnamen und aktiviert das Archiv auf demselben Dateisystem atomar. Vor jeder ARW-Bereinigung muss Phase 2 ein vollständiges JPG-Sicherungs-ZIP mit allen JPGs aus dem Batch-Hauptordner, `Review` und `Rejected` erzeugen, vollständig prüfen und hashprotokollieren. Zusätzlich muss ein ARW-Entscheidungs-ZIP nach der bisherigen Bash-Schutzlogik erzeugt werden. Es enthält die nach der finalen Sichtung noch durch aktive JPGs geschützten ARWs. Beide Archive werden per Dateiliste, Größe und SHA256 geprüft und atomar aktiviert. Kollisionen dürfen nie überschrieben werden. Ein ARW darf erst nach erfolgreicher Archivaktivierung und vollständiger Dokumentation gelöscht werden.
6. ARW-Bereinigung. Erst nach erfolgreicher Archivaktivierung und protokolliertem Archiv-Hash werden die betroffenen ARW-Dateien gelöscht; die Bereinigung wird mit Dateiliste und Hashes dokumentiert.
7. Abschluss und Übergabe an PHASE3. Nach vollständiger Archivierung und ARW-Bereinigung wird `phase2_completed` gesetzt. Der Batch verbleibt in `03_TEMP_DONE` und ist Kandidat für die optionale Phase 3.

### PHASE2-Vertrag

- Phase 2 muss nur für Batches mit `phase1_completed` und gültiger Freigabe (`03_TEMP_DONE` oder `automatic_handoff`) starten.
- Bei manueller Freigabe muss ein unveränderlicher `review_decision_record.json` mit `batch_id`, menschlicher Entscheidung, Vorhersage, Übereinstimmung, Konfigurationsfingerprint und Producer-Version geschrieben werden.
- Archivplan und Archiv-Inhalt müssen die im Archivvertrag definierten Pflichtfelder (relative Pfade, Größen, Hashes, Zeitstempel, Pfad zur ZIP, Entry-Count, Total-Size, Konfigurationsfingerprint, Producer-Version) enthalten.
- Ein ARW darf erst gelöscht werden, nachdem Archiv und Bereinigung vollständig dokumentiert sind; bei jedem Fehler bleibt das ARW erhalten.
- Phase 2 muss jeden Zustandsübergang atomar, mit Zeitstempel und Hash protokollieren; Rückwärts-Übergänge sind nur bei Quarantäne zulässig.

### PHASE2-Zustandsautomat

```text
phase1_completed
  → review_comparison_pending
  → review_record_committed
  → calibration_index_committed
  → phase2_archiving
  → phase2_completed
```

Bei einer explizit zugelassenen automatischen Übergabe:

```text
phase1_completed → automatic_handoff → phase2_archiving → phase2_completed
```

- Es entsteht kein Trainingslabel; Review-Record und Kalibrierungsindex werden für diesen Zweig nicht geschrieben.

**Blockierender Zustand:**

- `review_state_invalid` blockiert Phase 2 vollständig; der Batch wird nach `00_TEMP_ERROR` verschoben und als `blocking` gemeldet.
- In diesem Zustand darf keine ARW-Aktion stattfinden; eine spätere Bereinigung erfordert korrigierte Sichtung und erneute Freigabe.

**Beispiel (manuelle Freigabe):**

Ein Batch in `02_TEMP_IMAGES` wird vom Menschen vollständig gesichtet. Anschließend verschiebt der Mensch den gesamten Batch nach `03_TEMP_DONE`. Phase 2 validiert Manifest und Endentscheidungen, schreibt Review-Record und Kalibrierungsindex, erzeugt und aktiviert das Archiv atomar, dokumentiert die ARW-Bereinigung und setzt `phase2_completed`. Der Batch bleibt in `03_TEMP_DONE` und ist Kandidat für PHASE3.

## 3.4 PHASE3 Finalisierung, Veröffentlichung und Synology-Photos-API

- **Status:** Optional.
- **Zweck:** Erlaubt es, einen bereits erfolgreich durch PHASE2 verarbeiteten Batch kontrolliert zu veröffentlichen. Der Batch kann optional aus `03_TEMP_DONE` in einen von Synology Photos indexierten Zielpfad verschoben oder kopiert werden. Nach bestätigter Indexierung können vorhandene Workflow-Metadaten optional über einen gekapselten Synology-Photos-API-Adapter auf die indexierten Bilder übertragen werden.

### Ablauf

1. PHASE3 berücksichtigt ausschließlich Batches mit dem validen State `phase2_completed`.
2. `finalization.enabled: false` beendet PHASE3 ohne Datei- oder API-Aktion; der Batch bleibt unverändert in `03_TEMP_DONE`.
3. Bei `finalization.enabled: true` und `publish_to_synology_photos.enabled: false` validiert PHASE3 Konfiguration, State und Pfade und erzeugt nur Plan-/Reportartefakte; der Batch bleibt unverändert in `03_TEMP_DONE`.
4. Bei `publish_to_synology_photos.enabled: true` schreibt PHASE3 zuerst ein atomar validiertes `finalization_manifest.json` mit Quelle, Ziel, Modus, Dateiliste, Größen und SHA256-Hashes.
5. `mode: move` bedeutet zwingend `copy → verify → source removal`. Der vollständige Zielbestand wird zunächst aufgebaut und per Dateiliste, Größe und SHA256 verifiziert. Erst danach darf die Quelle entfernt werden. Diese Semantik gilt auch über unterschiedliche Dateisysteme hinweg und ist kein atomarer Dateisystem-Move; `mode: copy` kopiert den Batch und erhält die Quelle in `03_TEMP_DONE`.
6. Nach dem Transfer prüft PHASE3 die Vollständigkeit aller Zieldateien per Dateiliste, Größe und SHA256. Erst dann wird `phase3_transferred_to_target` gesetzt.
7. PHASE3 wartet mindestens `wait_for_index_seconds` und höchstens `max_index_wait_seconds` auf die Indexierung. Wird das Ziel innerhalb der Maximalwartezeit nicht eindeutig aufgelöst, wird `phase3_indexing_timeout` gesetzt. Der Zustand ist resume-fähig und löst keine Dateiaktion aus.
8. Nur bei `synology_api.enabled: true` und nach erfolgreicher Item-Auflösung überträgt der API-Adapter die erlaubten Metadaten. Die Werte werden aus bereits vorhandenen Workflow-Metadaten übernommen, nicht neu berechnet.
9. Bei aktivierter Rückleseprüfung liest PHASE3 die geschriebenen Werte erneut und bestätigt Rating, Tags und optionale Beschreibung.
10. Jeder Zustandsübergang, Transfer und API-Versuch wird atomar mit Zeitstempel, Konfigurationsfingerprint und Ergebnis protokolliert.

### PHASE3-Vertrag

- PHASE3 muss `batch_id`, `source_batch_path`, `target_batch_path` (falls Transfer aktiv), `publish_enabled`, `transfer_mode` (falls Transfer aktiv), `state`, `timestamp`, `config_fingerprint`, `producer_version` und `finalization_manifest_hash` enthalten.
- Bei API-Nutzung muss zusätzlich pro Bild ein lokaler Korrelationsrecord mit `relative_path`, `resolved_item_status`, `metadata_status`, `attempt_count` und `last_error` (optional, secrets-frei) geführt werden.

### PHASE3-Resume

- **Status:** Pflicht, wenn PHASE3 aktiviert ist.
- **Zweck:** Erlaubt es, einen unterbrochenen Finalisierungs-, Transfer-, Indexierungs- oder API-Lauf ohne doppelten Transfer, Datenverlust oder doppelte Tags sicher fortzusetzen.

### PHASE3-Zustandsautomat

```text
phase2_completed
  → phase3_finalization_planned
  → phase3_transfer_in_progress
  → phase3_transferred_to_target
  → phase3_index_waiting
  → phase3_item_resolution_pending
  → phase3_api_metadata_pending
  → phase3_api_metadata_completed
```

Bei deaktivierter Veröffentlichung:

```text
phase2_completed → phase3_finalization_planned → phase3_publish_disabled
```

`phase3_publish_disabled` ist kein Fehlerzustand. Er dokumentiert, dass PHASE3 bewusst keine Datei- oder API-Aktion ausführen durfte.

Zusaetzliche Fehlerzustände sind:

- `phase3_transfer_failed`
- `phase3_indexing_timeout`
- `phase3_item_resolution_failed`
- `phase3_api_metadata_partial`
- `phase3_api_metadata_failed`
- `finalization_state_invalid`

Ein PHASE3-Fehler darf keinen automatischen Rückwärts-Move auslösen. Ein bereits vollständig und hashgleich veröffentlichter Batch bleibt im Zielpfad; ein Folgejob setzt nur die noch fehlende Prüfung oder API-Metadatenoperation fort.

## 3.5 WorkUnits (Bildmengenmodus, Resume)

- **Status:** Pflicht.
- **Zweck:** Erlaubt es, auch sehr große physische Ordner in überschaubaren, sicher fortsetzbaren Portionen zu verarbeiten, ohne die sichtbare Ordnerstruktur zu verändern.

### Ablauf

1. `workflow.workunit_mode: source_batch` (Default, ganzer Ordner Einheit) oder `imagecount` (interne, unsichtbare Portionierung).
2. Der physische Batch wird erst verschoben, wenn alle WorkUnits abgeschlossen sind.
3. Angefangene oder wiederherzustellende Arbeit hat immer Vorrang vor neuen Ordnern.
4. Vor jedem sichtbaren Dateimove wird ein Übergangsstate `phase1_moving` geschrieben, erst danach der Abschluss `phase1_completed`.

**WorkUnit-Vertrag:** Eine WorkUnit muss `workunit_id`, `batch_id`, `image_range` (Start, Ende), `state` (pending, in_progress, completed, failed, paused), `timestamp`, `hash`, `error_reason` (optional) enthalten.

## 3.6 Archivvertrag

- ZIP: Lesbarkeit, Traversal, Größenlimit, Kompressionsverhältnis prüfen.
- Kollision: `...EXTRAn.zip` statt Überschreibung.
- Hash: SHA256 für ZIP, Manifest, State; Hash vor/nach Aktivierung prüfen.
- Aktivierung: Vollständiges Archiv erzeugt, geprüft, auf gleichem Dateisystem atomar aktiviert, mit Hash protokolliert.
- Löschung: ARW erst nach vollständig dokumentierter Bereinigung entfernen.

**Archiv-Vertrag-Kohärenz:** Jeder Archiveintrag muss folgende Felder enthalten:
- `relative_path` (string, relativ zum Batch)
- `size` (int, Bytes)
- `hash` (string, SHA256)
- `archived_at` (string, ISO8601)

**Archivplan-Details:**
- `batch_id`
- `created_at`
- `archive_path`
- `entry_count`
- `total_size`
- `entries`
- `config_fingerprint`
- `producer_version`

## 3.7 Fehler- und Recovery-Vertrag

- Fehlende oder ungültige Steuerdaten: Nach `WORKFLOW_DATA/runtime/quarantine` kopieren, mit Grund, Zeit und Hash melden; sichere Neuerstellung oder menschliche Prüfung erforderlich.
- Batch-Quarantäne: Unsichere oder blockierte Batches nach `00_TEMP_ERROR` verschieben und als `blocking` melden.
- Atomarität: Inhalt erzeugen, validieren, temporär auf demselben Dateisystem schreiben, erneut validieren und atomar ersetzen; die vorherige gültige Version bleibt bis zur Aktivierung erhalten.
- Lock: Globaler Lock verhindert parallele produktive Läufe; Lock vor und nach dem Lauf prüfen.
- Recovery: Ein Recovery darf Originale, Archive, Zustandsnachweise oder menschliche Entscheidungen nicht löschen.