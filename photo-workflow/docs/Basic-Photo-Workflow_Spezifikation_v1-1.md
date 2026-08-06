<!--
Basic Photo Workflow – Spezifikation v1.1
Datei: docs/Basic-Photo-Workflow_Spezifikation_v1-1.md
Mitentwickler: MaiTaiMa (in Zusammenarbeit mit Perplexity AI)
Erstellt: 2026-08-04
Projektversion: 1.1
Status: Vollstaendige, bereinigte und konsolidierte Fassung, erweitert um optionale PHASE3 (Finalisierung) und optionale Synology-Photos-API-Integration
-->

# Basic Photo Workflow – Spezifikation v1.1

**Zielsetzung:** Dieses Dokument ist die alleinige normative Quelle fuer Entwicklung, Betrieb, Test und Aenderungen. 

---

## 0. Geltungsbereich

### 0.1 Geltungsbereich und Zielsetzung

Diese Spezifikation definiert den produktiv sinnvollen Kern des Photo Workflow. Die Implementierung soll eine vorhandene Codebasis gezielt pruefen und nur die hier beschriebenen Funktionen ergaenzen oder reparieren. Sie soll nicht zu einer grossen allgemeinen Foto- oder Gesichtsdatenplattform ausgebaut werden.

Der Workflow verfolgt drei gleichrangige Ziele:

1. Originaldaten vor Verlust schuetzen.
2. Den wiederkehrenden manuellen Aufwand klein halten.
3. Die Qualitaet der Entscheidungen ueber nachvollziehbare Lernbeispiele verbessern.

Bei Zielkonflikten gilt die Abwaegungslogik aus 0.2.2

### 0.2 Lesart und Vorrang

#### 0.2.1 Normative Schluesselwoerter

Die Schluesselwoerter **MUSS**, **DARF NICHT**, **SOLL** und **KANN** sind normativ.

- **MUSS** kennzeichnet eine zwingende Anforderung.
- **DARF NICHT** kennzeichnet ein ausdrueckliches Verbot.
- **SOLL** kennzeichnet eine empfohlene Praxis.
- **KANN** kennzeichnet eine optionale Moeglichkeit.

#### 0.2.2 Abwaegungslogik

Bei Zielkonflikten gilt **zuerst** und **vorrangig vor allen anderen Regeln** folgende Abwaegungslogik:

1. **Sicherheit:** Keine unkontrollierten Datei aenderungen, Datenverluste oder unzulaessigen Datenuebertragungen. Geschuetzte Bilddaten, Face-Crops, Embeddings und Referenzbilder verlassen nie die erlaubten NAS-Datenbereiche. Lokale, ausdruecklich aktivierte Metadatenaufrufe an Synology Photos sind zulaessig, sofern keine Bilddaten oder Geheimnisse uebertragen werden.
2. **Stabilitaet:** Ein einzelnes fehlerhaftes Foto, ein Modellfehler oder ein defekter Ordner stoppt nicht den uebrigen sicheren Lauf.
3. **Nutzen:** Jede Funktion muss Fotos besser vorsortieren, Nachvollziehbarkeit oder Betriebssicherheit erhoehen.
4. **Einfachheit:** Wenige verstaendliche Optionen; keine technische Doppelstruktur ohne nachgewiesenen Nutzen.
5. **Performance:** Ein langsamer, begrenzter und ueber mehrere Tage fortsetzbarer Betrieb ist akzeptabel.

**Nichtnormativer Performance-Richtwert:** Auf einer typischen NAS (z. B. 2–4 Kerne, 4–8 GB RAM) sind ca. 500–1000 Bilder pro Tag realistisch. Embeddings werden nicht persistent gespeichert. Referenz-Embeddings werden nach einer Aenderung des aktiven Referenzpools oder nach einem Container-Neustart neu aufgebaut. Innerhalb eines laufenden Container-Laufs duerfen sie nur im RAM gecacht werden.

Diese Reihenfolge ist **verbindlich** und darf durch keine andere Regel, keine Konfiguration und keine Implementierungsentscheidung ueberstimmt werden. Sie gilt projektweit, fuer Fachlogik, Architektur, Konfiguration, Betrieb und Tests.

#### 0.2.3 Sekundaere Vorranghierarchie

Erst **nach** Anwendung der Abwaegungslogik aus 0.2.2 gilt in dieser Reihenfolge:

1. Datenintegritaet, Schutz von Originalen, Datenschutz und Sicherheitsgrenzen.
2. Ausdrueckliche Verbote.
3. Haupttext der Spezifikation.
4. Normative Anhaenge.
5. Nichtnormative Referenzwerte.

Ein Entwickler darf interne Algorithmen austauschen, wenn alle externen Vertraege, Artefaktformate, Sicherheitsgrenzen und Abnahmekriterien erhalten bleiben und die Abwaegungslogik aus 0.2.2 nicht verletzt wird.

---

## 1. Zielbild, Abwaegungslogik, Schutzgrenzen

### 1.1 Zielbild

Der Workflow verarbeitet Foto-Batches auf einem Synology-NAS in drei Phasen:

- **Phase 1** analysiert, bewertet und bereitet die menschliche Pruefung vor.
- **Phase 2** archiviert und bereinigt ARWs erst nach einer nachweislich sicheren Endentscheidung.
- **Phase 3** prueft einen erfolgreich abgeschlossenen Phase-2-Batch und kann ihn – nur bei aktivierter Veroeffentlichungsoption – aus `03_TEMP_DONE` in einen konfigurierten, von Synology Photos indexierten Zielpfad uebertragen. Nach erfolgreicher Indexierung KANN sie Ratings, kontrollierte Tags und optional Beschreibungen ueber einen Synology-Photos-API-Adapter anwenden. PHASE3 ist vollstaendig nachgelagert. Sie DARF nur fuer Batches mit `phase2_completed` starten. Sie DARF keine ARWs, ZIP-Archive, Review-Records, Referenzpools oder Kalibrierungsdaten veraendern. Ein Fehler in PHASE3 darf eine erfolgreiche PHASE2 weder zuruecksetzen noch Bilddaten loeschen.

Original-JPGs und ARWs duerfen weder still ueberschrieben noch geloescht werden. Bekannte Gesichtserkennung verarbeitet nur bewusst gepflegte bekannte Personen. Unbekannte Gesichter duerfen nicht gespeichert, geclustert, indexiert, getaggt, als Kandidat protokolliert oder als Referenz aktiviert werden. Ein Gesichtstreffer darf technische Mindestqualitaet, Manual Keep oder Schutzregeln niemals ueberstimmen.

### 1.2 Schutzgrenzen

Folgende Datenklassen unterliegen unterschiedlichen Schutzregeln:

| Klasse | Inhalt | Schutzregel |
|--------|--------|-------------|
| Originale | Kamera-JPGs und ARWs | Nur im geregelten Phasenablauf veraenderbar. Nie still ueberschreiben oder loeschen. |
| Abgeleitete Medien | Crops, ZIPs, Vorschauen, Kopien | Nur mit Herkunft, Hash und dokumentierter Aktion. |
| Steuerdaten | Manifeste, Zustaende, Logs, Indizes, Caches | Schema-validiert, atomar, rekonstruierbar. |
| Modellartefakte und Konfiguration | Modellgewichte, Config mit Pfaden | Duerfen separat verwaltet werden, sofern keine geschuetzten Bildinhalte exfiltriert werden. |

**Wichtig:** Bilddaten, Face-Crops, Embeddings und Referenzbilder werden nicht persistent ausserhalb der erlaubten Datenbereiche gespeichert. Modellartefakte und Konfigurationsdaten duerfen extern verwaltet werden, solange keine geschuetzten Bildinhalte uebertragen oder persistiert werden.

Automatisch erzeugte Face-Crops duerfen ausschliesslich in `WORKFLOW_DATA/faces/<slug>/new_faces/` persistent gespeichert werden. Die Verschiebung von `new_faces/` nach `reference/` erfolgt ausschliesslich manuell durch den Menschen. Erst danach gilt der Face-Crop als aktive Referenz und darf in `reference/` persistent liegen.

Bildbytes und Embeddings duerfen nie in JSON, Cache, Log, Manifest, CSV, Report, eingebetteten Metadaten oder API-Aufrufen persistiert werden. Embeddings sind ausschliesslich waehrend des aktiven Container-Laufs im RAM zulaessig.

### 1.3 Sicherheits- und Compliance-Grenzen

- Alle produktiven Arbeits-, Daten-, Archiv- und Referenzpfade muessen innerhalb von `paths.basedir` liegen.
- Ausschliesslich `finalization.publish_to_synology_photos.target_folder` darf innerhalb der separat validierten Wurzel `paths.publish_root` liegen.
- `paths.publish_root` MUSS ein lokaler NAS-Pfad sein, der von Synology Photos indexiert werden kann, fuer den Workflow schreibbar ist und keine Symlink-Aufloesung ausserhalb der erlaubten Wurzel zulaesst.
- `target_folder` MUSS innerhalb von `paths.publish_root` liegen.
- Die Pfadpruefung MUSS kanonische Pfade vergleichen und `..`-Traversal, unerlaubte Symlinks und unerlaubte Mountwechsel blockieren.
- Phase 2 benoetigt valide Freigabe, Locks, konsistenten Batch-State und verifizierte Archive.
- Archive werden nicht ueberschrieben; unsichere Kollisionen erzeugen neue Namen.
- Persistente Daten liegen ausserhalb des Container-Images.
- Private Bilder, Laufzeitdaten, lokale Secrets und Caches gehoeren nicht in Git.
- Die zentrale `config.yaml` bleibt secrets-frei.
- API-Credentials und Session-Token werden ausschliesslich ueber Container-Umgebungsvariablen bereitgestellt. Sie duerfen weder in Dateien noch in Batch-Manifests, CSVs, Logs, Reports oder Run-Summaries gespeichert werden.
- PHASE3 darf Quellpfade nur innerhalb von `paths.basedir` und Veroeffentlichungszielpfade nur innerhalb von `paths.publish_root` verwenden.
- Bei deaktiviertem Transfer darf PHASE3 keine Bilddatei aus `03_TEMP_DONE` verschieben, kopieren, loeschen oder umbenennen.
- Die API darf nur bereits vorhandene lokale Workflow-Metadaten uebertragen. Bildbytes, Face-Crops, Embeddings und Referenzbilder duerfen nicht an die API uebermittelt werden.
- API-Fehler duerfen niemals eine Loeschung, ein Ueberschreiben, einen Ruecktransfer oder eine sonstige unkontrollierte Dateiaenderung ausloesen.

---

## 2. Architektur, Verzeichnisse, Datenfluesse

### 2.1 Systemuebersicht

Das Projekt trennt Betriebsschnittstelle, CLI, Fachmodule und den persistenten NAS-Datenbereich. Shell-Skripte pruefen nur Umgebung und starten den Workflow; sie enthalten keine Geschaeftslogik. Die Python-CLI laedt `config/config.yaml`, validiert die Konfiguration und delegiert an spezialisierte Module. Die Fachmodule erzeugen testbare Ergebnisobjekte und kapseln Dateisystemmutationen.

### 2.2 Projektstruktur

- `NAS_EXAMPLE/`: Beispiel fuer den persistenten NAS-
  - `00_TEMP_ERROR/`: Quarantaene und Fehlerfaelle.
  - `01_TEMP_SD/`: Neue Eingangsbatches.
  - `02_TEMP_IMAGES/`: Phase-1-Review-Ausgabe.
  - `03_TEMP_DONE/`: Menschlich freigegebene Uebergabe.
  - `04_TEMP_FINAL/` (optional): Kontrollierter lokaler Finalisierungsbereich fuer erfolgreich durch PHASE2 verarbeitete Batches, wenn vor der Veroeffentlichung eine lokale Zwischenpruefung erforderlich ist.
  - `finalization.publish_to_synology_photos.target_folder`: Separat validierter Veroeffentlichungszielpfad innerhalb von `paths.publish_root`.
  - `WORKFLOW_DATA/`: States, Logs, Summaries, Caches, Referenzen, Modelle.
  - `MANUAL_KEEP/inbox/`: Manuelle Keep-Eingaenge.
  - `MANUAL_KEEP/used/`: Bereits zugeordnete Keep-Dateien.

- `photo-workflow/`
  - `app/`: Python-Fachmodule und CLI.
  - `config/`: Zentrale kommentierte Konfiguration.
  - `scripts/`: DSM-/Docker-Start- und Vorpruefungsskripte.
  - `tests/`: Unit- und Vertragspruefungen.
  - `docs/`: Handbuch, Architektur, Testdokumentation.

### 2.3 Kanonische Arbeitsordner

| Ordner | Zweck |
|--------|-------|
| `00_TEMP_ERROR` | Quarantaene fuer fehlerhafte oder unsichere Faelle. |
| `01_TEMP_SD` | Eingang fuer neue Kameraordner. |
| `02_TEMP_IMAGES` | Ergebnis aus Phase 1 zur manuellen Sichtung. |
| `03_TEMP_DONE` | Manuell freigegebene Ordner fuer Phase 2. |
| `04_TEMP_FINAL` (optional) | Kontrollierter lokaler Bereich fuer erfolgreich finalisierte Batches, sofern kein Direkttransfer nach `target_folder` genutzt wird. |
| `WORKFLOW_DATA` | Zentrale Daten (faces, models, runtime, samples, reports, archives, config). |
| `MANUAL_KEEP` | Vorab ausgewaehlte, extern erhaltene JPGs (inbox, used). |
| `finalization.publish_to_synology_photos.target_folder` | Optionaler Veroeffentlichungszielpfad. Er wird von Synology Photos indexiert. |

Die tatsaechlichen Arbeits-, Daten-, Archiv- und Referenzpfade muessen innerhalb von `paths.basedir` liegen. Der Veroeffentlichungszielpfad `target_folder` ist die einzige Ausnahme und muss innerhalb von `paths.publish_root` liegen. Beide Wurzeln und alle darunterliegenden Pfade werden kanonisch validiert.

`03_TEMP_DONE` bleibt der Arbeits- und Uebergabebereich nach manueller Freigabe und waehrend PHASE2. `04_TEMP_FINAL` kann als optionaler lokaler Finalisierungsbereich verwendet werden. Bei direktem Transfer wird der Batch nach `target_folder` uebertragen. Bei deaktivierter Veroeffentlichung bleibt der Batch in `03_TEMP_DONE` oder im kontrollierten `04_TEMP_FINAL` unveraendert.

### 2.4 Batch-Struktur und Benennung

Ein Batch enthaelt verbindlich die Unterordner:

- `ARW` (fuer ausgelagerte ARWs)
- `SAVE` (fuer JPG-Archiv und Scores)
- `Review` (fuer zur Pruefung vorgemerkte Bilder)
- `Rejected` (fuer abgelehnte Bilder)

Nur JPGs im Batch-Hauptordner gelten als aktiv. Ein aus `Review` oder `Rejected` in den Hauptordner zurueckgelegtes JPG ist wieder aktiv und schuetzt sein passendes ARW.

**ARW-Schutz:** Ein ARW ist geschuetzt, wenn ein aktives JPG mit demselben eindeutig normalisierten Basename existiert. Mehrdeutige Paarungen, mehrere wirksame JPG-Kopien, fehlende Quellhashes oder widerspruechliche Ordnerzustaende blockieren Phase 2 mit `review_state_invalid`; es darf keine ARW-Aktion stattfinden.

### 2.7 Manual Keep

**MANUAL_KEEP** ist der kontrollierte Eingang fuer externe, vorab ausgewaehlte JPGs (z. B. per WhatsApp erhalten). Die Zuordnung erfolgt streng getrennt vom Culling, Serienlogik und persoenlichen Geschmack. Die Vergleichsbilder können von der Auflösung und dem Dateinamen unterschiedlich zum Original sein.

- **inbox/**: Neue, noch nicht zugeordnete Manual-Keep-Bilder.
- **used/**: Bereits zugeordnete Manual-Keep-Bilder.

Detaillierte Logik: Siehe Abschnitt 4.6.

---

## 3. Batch-, Phasen- und Recovery-Vertrag

### 3.1 Batch-ID und Zustandsdatei

Die unveraenderliche `batch_id` lautet `source-folder-name+fingerprint(8)` und bleibt beim Wechsel zwischen allen Arbeitsordnern gleich. Pro Batch gibt es genau eine zentrale Zustandsdatei `WORKFLOW_DATA/runtime/state/{batch_id}.json`; globale Zustandsdateien sind unzulaessig.

**Batch-ID-Bildung:** Die `batch_id` wird bei Erstkontakt mit dem Batch aus dem Ordnernamen und einem 8-stelligen Fingerprint (SHA256, gekuerzt) gebildet. Sie bleibt ueber alle Ordnerwechsel hinweg unveraendert.

**Beispiel:** Ein Ordner `2024-08-15_Geburtstag` erhaelt die `batch_id` `2024-08-15_Geburtstag+a3f7c2e1`.

### 3.2 PHASE1 Aufbereitung, Bewertung und Ablage

- **Status:** Pflicht.
- **Zweck:** Phase 1 analysiert einen neuen Kamera-Batch, bewertet die Bilder und bereitet die menschliche Pruefung vor. Sie trennt ARWs von JPGs, normalisiert Datum und Namen, wendet Scoring, Serienlogik und Manual Keep an, schreibt Metadaten, CSV und das Phase-1-Manifest und uebergibt den Batch erst nach vollstaendiger, sichtbarer Ablage atomar nach `02_TEMP_IMAGES`.

- **Ablauf:**
  1. Stabilitaets-, Namens-, Lock- und Symlink-Pruefung. Der Batch MUSS groessen- und hashstabil sein; aktive Locks oder unsichere Symlinks blockieren die Verarbeitung.
  2. Datumsnormalisierung. Aufnahmedaten werden aus Metadaten ermittelt, konsistent normalisiert und in Dateinamen und Batch-Metadaten uebernommen.
  3. ARW-Ablage nach `ARW`. Alle ARW-Dateien werden vollstaendig und hashgeprueft in den Unterordner `ARW` verschoben; die Zuordnung zu ihren JPGs wird dokumentiert.
  4. Validiertes JPG-Archiv. JPGs werden auf Lesbarkeit, Integritaet und Dekodierbarkeit geprueft; fehlerhafte Dateien werden als Analysefehler gemeldet. Eine Bewertung oder Endentscheidung ohne sichtbar dokumentierten Fehlerstatus ist stilles Scoring und DARF NICHT stattfinden.
  5. Feature- und Score-Ermittlung einschliesslich Manual Keep und Serienlogik. Pro JPG werden technische Scores, persoenlicher Geschmack, Eye-Score und Family-Score berechnet. Serienlogik gruppiert aehnliche Bilder, Manual Keep erzwingt `keep` fuer erfolgreich zugeordnete extern ausgewaehlte Bilder.
  6. Eingebettete Metadaten, CSV und Phase-1-Manifest. Ratings, Tags und Status werden in die Bilder geschrieben, anschliessend rueckgelesen und geprueft; zusaetzlich entsteht `SAVE/culling_scores.csv` und ein JSON-Manifest mit Dateiliste, Countern, Hashes und Phase-1-Status.
  7. Sichtbare Ablage in Hauptordner, `Review` oder `Rejected`. Jedes Bild wird entsprechend seiner Endentscheidung im Batch-Hauptordner, in `Review` oder in `Rejected` abgelegt; nur JPGs im Hauptordner gelten als aktiv und schuetzen ihr ARW.
  8. Atomare Uebergabe nach `02_TEMP_IMAGES`. Erst nach vollstaendiger und konsistenter Ablage wird der Batch atomar nach `02_TEMP_IMAGES` uebergeben und der Zustand `phase1_completed` geschrieben.

**PHASE1-Vertrag:**

- Phase 1 MUSS genau einen zentralen Zustandsrecord pro `batch_id` in `WORKFLOW_DATA/runtime/state/{batch_id}.json` fuehren.
- Jeder Zustandsrecord MUSS mindestens `state`, `timestamp`, `hash` (SHA256 des vorherigen Zustands) und `producer_version` enthalten; `reason` ist optional bei Fehler oder Quarantaene.
- Phase-1-Ergebnisse MUESSEN mindestens `batch_id`, Pfade, Bildzaehler, ARW-Zaehler, Hash des `culling_scores.csv`, einen `manifest_hash` und den aktuellen Phase-/Review-/Kalibrierungsstatus enthalten.
- Das CSV MUSS pro Bild Scores, Serienmerkmale, Family-Match, Manual-Keep-Status und Metadatenstatus enthalten.
- Die sichtbare Ablage MUSS im Batch-Unterordner die kanonischen Ordner `ARW`, `SAVE`, `Review` und `Rejected` verwenden; sie DARF keine ARWs still ueberschreiben oder loeschen.

**PHASE1-Zustandsautomat:**

Fuer einen Batch in Phase 1 lautet der Kern-Zustandszweig:

```text
phase1_started → phase1_moving → phase1_completed
```

- `phase1_started` dokumentiert den Beginn der Phase-1-Verarbeitung fuer einen neu erkannten Batch.
- `phase1_moving` dokumentiert, dass die sichtbare Batch-Uebergabe begonnen hat. Der Zustand wird vor dem sichtbaren Dateimove atomar geschrieben.
- `phase1_completed` dokumentiert, dass alle acht Schritte der Phase 1 erfolgreich abgeschlossen und die Ergebnisse atomar nach `02_TEMP_IMAGES` uebergeben wurden.

Zwischenzustand und Fehlerdetails werden ueber die allgemeine Zustandsdatei und Quarantaene abgebildet. Rueckwaerts-Uebergaenge sind nur bei Quarantaene zulaessig.

**Beispiel:**

Ein Ordner `2024-08-15_Geburtstag` wird nach `01_TEMP_SD` kopiert und erhaelt die `batch_id` `2024-08-15_Geburtstag+a3f7c2e1`. Phase 1 prueft Stabilitaet und Symlinks, normalisiert Datum und Namen, lagert alle ARWs nach `ARW` aus, berechnet Scoring, Serien und Manual Keep, schreibt Metadaten und Manifest und legt die Bilder in Hauptordner, `Review` und `Rejected` ab. Anschliessend wird der Batch atomar nach `02_TEMP_IMAGES` verschoben und der Zustand `phase1_completed` geschrieben.

---

### 3.3 PHASE2 Archivierung und ARW-Bereinigung

- **Status:** Pflicht fuer freigegebene Batches.
- **Zweck:** Phase 2 archiviert einen nach Phase 1 fertig sortierten und vom Menschen gesichteten Batch und bereinigt kontrolliert die ARW-Dateien. Sie MUSS zuerst Phase-1-Manifest und Endentscheidungen validieren, bei manueller Freigabe einen unveraenderlichen Review-Record schreiben und erst danach archivieren. Ein ARW DARF nur geloescht werden, nachdem ein vollstaendiges Archiv erzeugt, geprueft, auf demselben Dateisystem atomar aktiviert und mit Hash protokolliert wurde. Bei jedem Fehler bleibt das ARW erhalten.

- **Ablauf:**
  1. Phase-2-Start. Phase 2 beginnt erst nach manueller Freigabe durch Move des gesamten Batches nach `03_TEMP_DONE` oder nach explizit zugelassener automatischer Uebergabe (`automatic_handoff`). Die automatische Uebergabe ist nur zulaessig, wenn `phase2.automatic_handoff.enabled: true` gesetzt ist. Zusaetzlich duerfen keine JPGs in `Review` liegen und kein Bild darf `analysis_error` tragen. Bei deaktiviertem Flag ist ausschliesslich die manuelle Freigabe durch Verschieben des vollstaendigen Batches nach `03_TEMP_DONE` zulaessig.
  2. Validierung von Phase-1-Manifest und Endentscheidungen. Das Phase-1-Manifest, die sichtbare Ordnerstruktur und die Zuordnung ARW↔JPG werden geprueft.
  3. Blockierender Zustand `review_state_invalid`. Mehrdeutige Paarungen, mehrere wirksame JPG-Kopien, fehlende Quellhashes oder widerspruechliche Ordnerzustaende setzen `review_state_invalid`; der Batch wird nach `00_TEMP_ERROR` verschoben und als `blocking` gemeldet. Es DARF keine ARW-Aktion stattfinden.
  4. Review-Record und Kalibrierungsindex (manuelle Freigabe). Bei manueller Freigabe MUSS zuerst ein unveraenderlicher Review-Record mit menschlicher Endentscheidung geschrieben werden, danach ein Kalibrierungsindex fuer den Gewichtungsassistenten.
  5. Archivierung. Phase 2 erzeugt ein Archiv gemaess Archivvertrag, prueft es vollstaendig per Dateiliste, Groesse und SHA256, behandelt Namenskollisionen durch neue Archivnamen und aktiviert das Archiv auf demselben Dateisystem atomar. Vor jeder ARW-Bereinigung MUSS Phase 2 ein vollstaendiges JPG-Sicherungs-ZIP mit allen JPGs aus dem Batch-Hauptordner, `Review` und `Rejected` erzeugen, vollstaendig pruefen und hashprotokollieren. Zusaetzlich MUSS ein ARW-Entscheidungs-ZIP nach der bisherigen Bash-Schutzlogik erzeugt werden. Es enthaelt die nach der finalen Sichtung noch durch aktive JPGs geschuetzten ARWs. Beide Archive werden per Dateiliste, Groesse und SHA256 geprueft und atomar aktiviert. Kollisionen duerfen nie ueberschrieben werden. Ein ARW darf erst nach erfolgreicher Archivaktivierung und vollstaendiger Dokumentation geloescht werden.
  6. ARW-Bereinigung. Erst nach erfolgreicher Archivaktivierung und protokolliertem Archiv-Hash werden die betroffenen ARW-Dateien geloescht; die Bereinigung wird mit Dateiliste und Hashes dokumentiert.
  7. Abschluss und Uebergabe an PHASE3. Nach vollstaendiger Archivierung und ARW-Bereinigung wird `phase2_completed` gesetzt. Der Batch verbleibt in `03_TEMP_DONE` und ist Kandidat fuer die optionale Phase 3.

**PHASE2-Vertrag:**

- Phase 2 MUSS nur fuer Batches mit `phase1_completed` und gueltiger Freigabe (`03_TEMP_DONE` oder `automatic_handoff`) starten.
- Bei manueller Freigabe MUSS ein unveraenderlicher `review_decision_record.json` mit `batch_id`, menschlicher Entscheidung, Vorhersage, Uebereinstimmung, Konfigurationsfingerprint und Producer-Version geschrieben werden.
- Archivplan und Archiv-Inhalt MUESSEN die im Archivvertrag definierten Pflichtfelder (relative Pfade, Groessen, Hashes, Zeitstempel, Pfad zur ZIP, Entry-Count, Total-Size, Konfigurationsfingerprint, Producer-Version) enthalten.
- Ein ARW DARF erst geloescht werden, nachdem Archiv und Bereinigung vollstaendig dokumentiert sind; bei jedem Fehler bleibt das ARW erhalten.
- Phase 2 MUSS jeden Zustandsuebergang atomar, mit Zeitstempel und Hash protokollieren; Rueckwaerts-Uebergaenge sind nur bei Quarantaene zulaessig.

**PHASE2-Zustandsautomat (manuell und automatisch):**

Fuer manuell freigegebene Batches lautet der zwingende Zustandszweig:

```text
phase1_completed
  → review_comparison_pending
  → review_record_committed
  → calibration_index_committed
  → phase2_archiving
  → phase2_completed
```

- Der manuelle Move des gesamten Batches von `02_TEMP_IMAGES` nach `03_TEMP_DONE` ist das alleinige Freigabesignal fuer diesen Zweig.
- `review_comparison_pending` markiert die Phase, in der automatische Entscheidungen gegen die menschliche Sichtung verglichen werden.
- `review_record_committed` haelt den unveraenderlichen Review-Record fest.
- `calibration_index_committed` dokumentiert, dass der Kalibrierungsindex fuer den Gewichtungsassistenten geschrieben wurde.
- `phase2_archiving` umfasst Archivierung und ARW-Bereinigung.

Bei einer explizit zugelassenen automatischen Uebergabe lautet der Zustandsautomat:

```text
phase1_completed → automatic_handoff → phase2_archiving → phase2_completed
```

- Es entsteht kein Trainingslabel; Review-Record und Kalibrierungsindex werden fuer diesen Zweig nicht geschrieben.

**Blockierender Zustand:**

- `review_state_invalid` blockiert Phase 2 vollstaendig; der Batch wird nach `00_TEMP_ERROR` verschoben und als `blocking` gemeldet.
- In diesem Zustand DARF keine ARW-Aktion stattfinden; eine spaetere Bereinigung erfordert korrigierte Sichtung und erneute Freigabe.

**Beispiel (manuelle Freigabe):**

Ein Batch in `02_TEMP_IMAGES` wird vom Menschen vollstaendig gesichtet. Anschliessend verschiebt der Mensch den gesamten Batch nach `03_TEMP_DONE`. Phase 2 validiert Manifest und Endentscheidungen, schreibt Review-Record und Kalibrierungsindex, erzeugt und aktiviert das Archiv atomar, dokumentiert die ARW-Bereinigung und setzt `phase2_completed`. Der Batch bleibt in `03_TEMP_DONE` und ist Kandidat fuer PHASE3.

---

### 3.4 PHASE3 Finalisierung, Veroeffentlichung und Synology-Photos-API

- **Status:** Optional.
- **Zweck:** Erlaubt es, einen bereits erfolgreich durch PHASE2 verarbeiteten Batch kontrolliert zu veroeffentlichen. Der Batch kann optional aus `03_TEMP_DONE` in einen von Synology Photos indexierten Zielpfad verschoben oder kopiert werden. Nach bestaetigter Indexierung koennen vorhandene Workflow-Metadaten optional ueber einen gekapselten Synology-Photos-API-Adapter auf die indexierten Bilder uebertragen werden.

- **Ablauf:**
  1. PHASE3 beruecksichtigt ausschliesslich Batches mit dem validen State `phase2_completed`.
  2. `finalization.enabled: false` beendet PHASE3 ohne Datei- oder API-Aktion; der Batch bleibt unveraendert in `03_TEMP_DONE`.
  3. Bei `finalization.enabled: true` und `publish_to_synology_photos.enabled: false` validiert PHASE3 Konfiguration, State und Pfade und erzeugt nur Plan-/Reportartefakte; der Batch bleibt unveraendert in `03_TEMP_DONE`.
  4. Bei `publish_to_synology_photos.enabled: true` schreibt PHASE3 zuerst ein atomar validiertes `finalization_manifest.json` mit Quelle, Ziel, Modus, Dateiliste, Groessen und SHA256-Hashes.
  5. `mode: move` bedeutet zwingend `copy → verify → source removal`. Der vollständige Zielbestand wird zunächst aufgebaut und per Dateiliste, Größe und SHA256 verifiziert. Erst danach darf die Quelle entfernt werden. Diese Semantik gilt auch über unterschiedliche Dateisysteme hinweg und ist kein atomarer Dateisystem-Move; `mode: copy` kopiert den Batch und erhaelt die Quelle in `03_TEMP_DONE`.
  6. Nach dem Transfer prueft PHASE3 die Vollstaendigkeit aller Zieldateien per Dateiliste, Groesse und SHA256. Erst dann wird `phase3_transferred_to_target` gesetzt.
  7. PHASE3 wartet mindestens `wait_for_index_seconds` und höchstens `max_index_wait_seconds` auf die Indexierung. Wird das Ziel innerhalb der Maximalwartezeit nicht eindeutig aufgelöst, wird `phase3_indexing_timeout` gesetzt. Der Zustand ist resume-fähig und löst keine Dateiaktion aus.
  8. Nur bei `synology_api.enabled: true` und nach erfolgreicher Item-Aufloesung uebertraegt der API-Adapter die erlaubten Metadaten. Die Werte werden aus bereits vorhandenen Workflow-Metadaten uebernommen, nicht neu berechnet.
  9. Bei aktivierter Ruecklesepruefung liest PHASE3 die geschriebenen Werte erneut und bestaetigt Rating, Tags und optionale Beschreibung.
  10. Jeder Zustandsuebergang, Transfer und API-Versuch wird atomar mit Zeitstempel, Konfigurationsfingerprint und Ergebnis protokolliert.

**PHASE3-Vertrag:**

- PHASE3 MUSS `batch_id`, `source_batch_path`, `target_batch_path` (falls Transfer aktiv), `publish_enabled`, `transfer_mode` (falls Transfer aktiv), `state`, `timestamp`, `config_fingerprint`, `producer_version` und `finalization_manifest_hash` enthalten.
- Bei API-Nutzung MUSS zusaetzlich pro Bild ein lokaler Korrelationsrecord mit `relative_path`, `resolved_item_status`, `metadata_status`, `attempt_count` und `last_error` (optional, secrets-frei) gefuehrt werden.

**Beispiele:**

- **Beispiel ohne Veroeffentlichung:** Bei `finalization.enabled: true` und `publish_to_synology_photos.enabled: false` wird ein Batch `2024-08-15_Geburtstag+a3f7c2e1` mit `phase2_completed` geprueft und in der Run-Summary als `finalization_skipped_publish_disabled` gemeldet. Er verbleibt vollstaendig in `03_TEMP_DONE`; keine Datei wird verschoben oder kopiert und keine API wird aufgerufen.
- **Beispiel mit Copy:** Bei `finalization.enabled: true`, `publish_to_synology_photos.enabled: true` und `mode: copy` wird der Batch von `/photo/03_TEMP_DONE/2024-08-15_Geburtstag` nach `/volume1/photo/Workflow/2024-08-15_Geburtstag` kopiert. Erst wenn alle Dateien im Ziel hashgleich vorliegen, wird `phase3_transferred_to_target` gesetzt. Die Quelle bleibt in `03_TEMP_DONE` erhalten.
- **Beispiel mit Move:** Bei `mode: move` wird zunaechst der vollstaendige Zielbestand aufgebaut und geprueft. Erst nach erfolgreichem Abgleich darf die Quelle als Move-Abschluss entfernt werden. Scheitert ein Schritt, bleibt ein sicherer, wiederaufnehmbarer Zustand erhalten; es darf kein Bild verloren gehen.

**PHASE3-Resume:**

- **Status:** Pflicht, wenn PHASE3 aktiviert ist.
- **Zweck:** Erlaubt es, einen unterbrochenen Finalisierungs-, Transfer-, Indexierungs- oder API-Lauf ohne doppelten Transfer, Datenverlust oder doppelte Tags sicher fortzusetzen.

- **Ablauf:**
  1. Vor einer Dateiaktion erzeugt PHASE3 ein atomar validiertes `finalization_manifest.json`.
  2. Ist die Veroeffentlichung deaktiviert, wird `phase3_publish_disabled` gesetzt; bei spaeterer Aktivierung wird kein alter Plan blind wiederverwendet, sondern mit dem aktuellen Konfigurationsfingerprint neu geprueft.
  3. Ist die Quelle vollstaendig und das Ziel nicht vorhanden, wird der Transfer nach dem gespeicherten Modus fortgesetzt oder neu geplant.
  4. Ist das Ziel vollstaendig und hashgleich, wird kein zweiter Transfer ausgefuehrt; PHASE3 setzt bei Indexierung, Item-Aufloesung oder API-Metadaten fort.
  5. Sind Quelle und Ziel gleichzeitig vorhanden, entscheidet das Manifest: Bei `copy` ist dies erwartbar; bei `move` wird geprueft, ob der Move noch nicht finalisiert wurde.
  6. Bei abweichenden Hashes, unklarer Teiluebertragung oder einer Kollision wird der Batch blockiert und in der Run-Summary als `blocking` gemeldet.

**Finalization-Manifest-Vertrag:** `finalization_manifest.json` MUSS `schema_version`, `batch_id`, `created_at`, `updated_at`, `producer_version`, `source_batch_path`, `target_batch_path` (optional, wenn Veroeffentlichung deaktiviert), `publish_enabled`, `mode` (optional), `entries` (relative_path, size, hash), `config_fingerprint`, `state` und `hash` enthalten.

**Beispiel Resume:** Ein Copy-Lauf mit 800 Bildern wird nach 600 Dateien unterbrochen. Beim naechsten Start vergleicht PHASE3 Quelle, Ziel und Transfermanifest. Bereits vollstaendig hashgleiche Zieldateien werden nicht erneut kopiert; fehlende Dateien werden ergaenzt. Erst nach vollstaendigem Hashabgleich folgt die Indexierungs- und API-Phase.

**PHASE3-Zustandsautomat:**

Fuer einen Batch mit aktivierter Veroeffentlichung lautet der optionale Zustandszweig:

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

Fuer einen Batch mit aktiver PHASE3, aber deaktivierter Veroeffentlichung lautet der Abschluss:

```text
phase2_completed → phase3_finalization_planned → phase3_publish_disabled
```

PHASE3 darf entweder direkt von `03_TEMP_DONE` nach `target_folder` übertragen oder den optionalen Bereich `04_TEMP_FINAL` als kontrollierte lokale Zwischenstufe verwenden. Teilübertragungen gelten nie als erfolgreich veröffentlicht.

`phase3_publish_disabled` ist kein Fehlerzustand. Er dokumentiert, dass PHASE3 bewusst keine Datei- oder API-Aktion ausfuehren durfte.

Zusaetzliche Fehlerzustaende sind:

- `phase3_transfer_failed`
- `phase3_indexing_timeout`
- `phase3_item_resolution_failed`
- `phase3_api_metadata_partial`
- `phase3_api_metadata_failed`
- `finalization_state_invalid`

Ein PHASE3-Fehler darf keinen automatischen Rueckwaerts-Move ausloesen. Ein bereits vollstaendig und hashgleich veroeffentlichter Batch bleibt im Zielpfad; ein Folgejob setzt nur die noch fehlende Pruefung oder API-Metadatenoperation fort.

### 3.5 WorkUnits (Bildmengenmodus, Resume)

- **Status:** Pflicht.
- **Zweck:** Erlaubt es, auch sehr grosse physische Ordner in ueberschaubaren, sicher fortsetzbaren Portionen zu verarbeiten, ohne die sichtbare Ordnerstruktur zu veraendern.
- **Ablauf:**
  1. `workflow.workunit_mode: source_batch` (Default, ganzer Ordner Einheit) oder `imagecount` (interne, unsichtbare Portionierung).
  2. Der physische Batch wird erst verschoben, wenn alle WorkUnits abgeschlossen sind.
  3. Angefangene oder wiederherzustellende Arbeit hat immer Vorrang vor neuen Ordnern.
  4. Vor jedem sichtbaren Dateimove wird ein Uebergangsstate `phase1_moving` geschrieben, erst danach der Abschluss `phase1_completed`.

**WorkUnit-Vertrag:** Eine WorkUnit MUSS `workunit_id`, `batch_id`, `image_range` (Start, Ende), `state` (pending, in_progress, completed, failed, paused), `timestamp`, `hash`, `error_reason` (optional) enthalten.

**Beispiel imagecount:** Bei `workflow.workunit_mode: imagecount` und `workflow.images_per_workunit: 200` wird ein physischer Batch mit 800 Bildern in 4 WorkUnits aufgeteilt. Jede WorkUnit wird separat verarbeitet, aber der Batch wird erst nach Abschluss aller 4 WorkUnits nach `02_TEMP_IMAGES` verschoben.

### 3.6 Archivvertrag

- **ZIP:** Lesbarkeit, Traversal, Groessenlimit, Kompressionsverhaeltnis pruefen.
- **Kollision:** `...EXTRAn.zip` statt Ueberschreibung.
- **Hash:** SHA256 fuer ZIP, Manifest, State; Hash vor/nach Aktivierung pruefen.
- **Aktivierung:** Vollstaendiges Archiv erzeugt, geprueft, auf gleichem Dateisystem atomar aktiviert, mit Hash protokolliert.
- **Loeschung:** ARW erst nach vollstaendig dokumentierter Bereinigung entfernen.

**Archiv-Vertrag-Kohaerenz:** Jeder Archiveintrag MUSS folgende Felder enthalten:
- `relative_path` (string, relativ zum Batch)
- `size` (int, Bytes)
- `hash` (string, SHA256)
- `archived_at` (string, ISO8601)

**Archivplan-Details:** Der Archivplan MUSS folgende Felder enthalten:
- `batch_id` (Batch-ID)
- `created_at` (ISO8601-Zeitstempel)
- `archive_path` (relativer Pfad zur ZIP)
- `entry_count` (Anzahl der Eintraege)
- `total_size` (Gesamtgroesse in Bytes)
- `entries` (Liste aller Eintraege mit Pfad, Groesse, SHA256)
- `config_fingerprint` (SHA256 der effektiven Konfiguration)
- `producer_version` (Versionskennung)

### 3.7 Fehler- und Recovery-Vertrag

- **Fehlende oder ungültige Steuerdaten:** Nach `WORKFLOW_DATA/runtime/quarantine` kopieren, mit Grund, Zeit und Hash melden; sichere Neuerstellung oder menschliche Prüfung erforderlich.
- **Batch-Quarantäne:** Unsichere oder blockierte Batches nach `00_TEMP_ERROR` verschieben und als `blocking` melden.
- **Atomarität:** Inhalt erzeugen, validieren, temporär auf demselben Dateisystem schreiben, erneut validieren und atomar ersetzen; die vorherige gültige Version bleibt bis zur Aktivierung erhalten.
- **Lock:** Globaler Lock verhindert parallele produktive Läufe; Lock vor und nach dem Lauf prüfen.
- **Recovery:** Ein Recovery darf Originale, Archive, Zustandsnachweise oder menschliche Entscheidungen nicht löschen.

---

## 4. Scoring, Serien, Metadaten, Manual Keep, Face-Backend, Kalibrierung

### 4.1 Technisches Culling (basescore)

- **Status:** Pflicht.
- **Zweck:** Ressourcenschonende Basisbewertung ohne Pflicht-KI-Modell. Bewertet Schaerfe, Belichtung und einfache aesthetische Merkmale. Ergebnis ist `base_score`.
- **Ablauf:**
  1. Kleine technische Vorschau erzeugen (256–512 Pixel laengste Kante).
  2. Teilscores fuer Schaerfe (Kantenvarianz), Belichtung (Clipping), Helligkeitsbalance und Aesthetik (Kontrast, Saettigung, Bildbalance) berechnen.
  3. Teilscores mit konfigurierbaren Gewichten (`culling.base_weights`) zu `base_score` kombinieren.
  4. Nicht lesbare oder fehlerhafte Bilder erhalten `analysis_error`, aber keinen stillen Ersatzscore.

**Score-Vertrag:** `base_score` ist eine Fliesskommazahl im Bereich [0,0 bis 1,0]. `analysis_error` wird als `null` oder spezieller Wert `-1` repraesentiert, nie als 0.0.

### 4.2 Persoenlicher Geschmack (lokales CLIP, personal_score)

- **Status:** Pflicht.
- **Zweck:** Ergaenzt die technische Bewertung um eine gelernte, persoenliche Praeferenz. Bewertet Bilder gegen positive/negative Text-Prompts oder aktive Referenzbilder.
- **Ablauf:**
  1. CLIP-Modell laedt nur bei aktiviertem Adapter.
  2. Bild wird gegen aktive Referenzen aus `samples/reference` oder gegen Prompt-Listen bewertet.
  3. Ergebnis ist ausschliesslich `personal_score`; es wird nicht in `base_score` gemischt.
  4. Bilder, die `keep` sind, hoechste Sternklasse erreichen und die aktive Auswahl messbar erweitern, werden automatisch nach `samples/new_refs` vorgeschlagen.
  5. Nur ein manuelles Kopieren nach `samples/reference` aktiviert sie und loest ein Retraining aus.

**Score-Vertrag:** `personal_score` ist eine Fliesskommazahl im Bereich [0,0 bis 1,0] oder `None` bei deaktiviertem/fehlerhaftem Adapter.

### 4.3 Serienerkennung (series_id, series_rank, series_best)

- **Status:** Pflicht.
- **Zweck:** Verhindert, dass mehrere technisch aehnliche Aufnahmen alle gleich behandelt werden. Hebt das beste Bild einer Serie hervor.
- **Ablauf:**
  1. Gruppierung ueber Aufnahmezeit, Bild-Embedding, visuelle Aehnlichkeit oder deterministische Dateinamenlogik als Fallback.
  2. Pro Bild werden Serien-ID, -Groesse, -Rang, `series_best`-Flag und Abstand zum Besten gespeichert.
  3. Das Bestbild darf hoechstens um eine Klasse aufgewertet werden.
  4. Andere Bilder duerfen nur mit dokumentierter Distanz zum Bestbild abgewertet werden.

**Serien-Vertrag:** `series_id` ist eine eindeutige Zeichenkette pro Serie innerhalb eines Batches. `series_rank` ist 1-basiert (1 = bestes Bild). `series_best` ist ein boolescher Wert.

### 4.4 Eye-Score (geschlossene Augen)

- **Status:** Pflicht.
- **Zweck:** Erkennt geschlossene Augen als leichtes Korrektursignal.
- **Ablauf:**
  1. Nur bei genau einem ausreichend grossem Gesicht im Bild.
  2. ONNX-Zweiklassen-Modell liefert `P(offen)`.
  3. Ergebnis ist `eye_score` (eigene Komponente, nicht Teil von `base_score`).

**Score-Vertrag:** `eye_score` ist eine Fliesskommazahl im Bereich [0,0 bis 1,0] (Wahrscheinlichkeit fuer offene Augen) oder `None`.

### 4.5 Bekannte Gesichtserkennung (Familie, `family_score`)

- **Status:** Pflicht, sobald der Face-Adapter aktiviert ist.
- **Zweck:** Liefert ein moderates positives Signal für bewusst gepflegte, bekannte Personen. Keine allgemeine Gesichtserkennung, kein Clustering unbekannter Gesichter.
- **Ablauf:**
  1. Das registrierte Backend erzeugt ein Embedding ausschließlich flüchtig im RAM.
  2. Der Vergleich erfolgt gegen aktive Referenzen einer Person unter `faces/<slug>/reference` mit `selection.json` und Status `active`.
  3. Nur bei eindeutigem Match mit Schwelle und Sicherheitsmarge zum Zweitbesten wird `family_score` gesetzt und ein Personentag vergeben.
  4. Neue Face-Crop-Vorschläge werden ausschließlich unter `faces/<slug>/new_faces` persistent gespeichert.
  5. Die Verschiebung eines Vorschlags von `new_faces` nach `reference` erfolgt ausschließlich manuell durch den Menschen. Automatische Aktivierung ist verboten.

**Schutzgrenzen:** Bildbytes und Embeddings dürfen nie in JSON, Cache, Log, Manifest, CSV, Metadaten oder Report persistiert werden. Automatisch erzeugte Face-Crops dürfen nur in `new_faces` geschrieben werden. Nach manueller Aktivierung dürfen sie als aktive Referenzen in `reference` liegen.

**Face-Backend-Vertrag:** Jedes Backend MUSS Registry-ID, Adaptername, Modellhash, Provider, Vorverarbeitung, Metrik und Auswahlfingerprint bereitstellen.

**Score-Vertrag:** `family_score` ist eine Fließkommazahl im Bereich [0,0 bis 1,0] oder `None`.

### 4.6 Manual Keep (manual_keep, manual_keep_match)

- **Status:** Pflicht.
- **Zweck:** Ordnet extern (z. B. per WhatsApp) vorab ausgewaehlte, oft komprimierte/kleine Bilder ihrem Original im aktuellen Batch zu und erzwingt fuer dieses `keep`.
- **Ablauf:**
  1. Zweistufig: schneller aufloesungsrobuster Vorfilter (Seitenverhaeltnis, Perceptual Hash).
  2. Danach strenge normalisierte Endpruefung (Verifikationsscore auf EXIF-korrigierten, gleich skalierten Bildern).
  3. Match nur bei Schwelle und ausreichendem Abstand zum Zweitbesten.
  4. Ergebnis erzwingt `keep` mit Grund `manual_keep_match`.
  5. Danach durchlaeuft das Bild normales Scoring; erst nach Zuordnung wird die Quelldatei nach `used` verschoben.

**Manual-Keep-Vertrag:** `manual_keep` ist ein boolescher Wert (`true` bei Match, `false` oder `null` sonst). `manual_keep_match` wird in der Run-Summary als Zaehler gefuehrt.

### 4.7 Metadaten (Rating, Tags, Beschreibung)

- **Status:** Pflicht.
- **Zweck:** Macht Bewertungen und Personentreffer in gaengigen Fotoprogrammen sichtbar.
- **Ablauf:**
  1. Sternrating aus Score-Band bestimmen.
  2. Namespaced Keywords einbetten (`workflow:ai_cull`, `decision:final`, `series:`, `family:match`, `person:<slug>`, `manual_keep:true`).
  3. Per `exiftool` (shell=False) in Bild schreiben.
  4. Nach dem Schreiben zuruecklesen und abgleichen.

**Metadaten-Vertrag:** Metadaten MUessen namespaced sein (Praefix `workflow:`). `failed_metadata` ist ein boolescher Wert. `exiftool_status` ist einer von `success`, `disabled`, `failed`, `sidecar`.

### 4.8 Kalibrierung und Gewichtungsassistent

- **Status:** Pflicht.
- **Zweck:** Lernt aus bestaetigten menschlichen Endentscheidungen, ob die vorhandenen Score-Komponenten anders gewichtet werden sollten. Ersetzt nie die Komponenten selbst.
- **Ablauf:**
  1. Pro manuell freigegebenem Batch entsteht ein unveraenderliches `review_decision_record.json`.
  2. Daraus werden Kennzahlen (terminale Uebereinstimmung, `reject_to_keep_rate` etc.) berechnet.
  3. Optional wird ein Gewichtsvorschlag im Schattenmodus erzeugt.
  4. Eine Aktivierung erfordert bewusste Nutzerfreigabe, erfuellte Gates und bleibt jederzeit rollbackfaehig.

**Kalibrierungs-Vertrag:** `review_decision_record.json` MUSS `batch_id`, `timestamp`, `human_decision`, `predicted_decision`, `agreement`, `config_fingerprint`, `producer_version` enthalten.

---

## 5. Referenzpool-Verwaltung, Rebuild und Nutzen-Ranking 
- **Status:** Pflicht, sobald der Geschmacks- oder Face-Adapter aktiviert ist.
### 5.1 Ziel

Die Referenzpool-Verwaltung ist die gemeinsame Regel fuer Geschmack und bekannte Gesichter. Sie stellt sicher, dass aktive Referenzen klein, qualitativ sinnvoll und divers bleiben. Sie trennt Vorschlagsdateien von aktiven Referenzen, erzwingt menschliche Freigabe, aktualisiert Wahrheitsdateien und baut bei jeder aktiven Aenderung die Referenzbasis neu auf.

### 5.2 Geltungsbereich

Diese Regeln gelten fuer:
- Face-Referenzpools: `WORKFLOW_DATA/faces/<slug>` (je bekannte Person)
- Geschmacks-Referenzpool: `WORKFLOW_DATA/samples`

Nicht Gegenstand dieser Regel sind Manual Keep, technische Culling-Bilder (ausserhalb der speziell konfigurierten Modellbasis) und unbekannte Gesichter.

### 5.3 Ordnerstruktur

Jeder Pool MUSS folgende Struktur haben:

```text
pool_root/
  reference/          # Aktive Referenzen (max. max_active)
  new/                # Vorschlaege (max. max_new, max. max_new_per_batch pro Batch)
  selection.json      # EINZIGE Wahrheit fuer diesen Pool
```

- Face: `pool_root = WORKFLOW_DATA/faces/<slug>`, `new = new_faces`, Dateien = Face-Crops.
- Geschmack: `pool_root = WORKFLOW_DATA/samples`, `new = new_refs`, Dateien = Ganzbilder.

Bei Face-Pools werden neue Face-Crops automatisch ausschließlich in `new_faces/` gespeichert. Die manuelle Verschiebung nach `reference/` ist der einzige Aktivierungsschritt. Bei Geschmackspools werden Vorschläge in `new_refs/` gespeichert und ebenfalls nur manuell nach `reference/` aktiviert.

### 5.4 Wahrheitsdatei (selection.json)

Jeder Pool hat genau eine `selection.json` im Hauptordner. Sie ist die alleinige Wahrheit ueber aktive Referenzen, offene Vorschlaege, Kapazitaetsgrenzen, Auswahlfingerprint und Rangdetails.

**Pflichtfelder:**
- `schema_version`
- `pool_type`
- `slug` (nur Face)
- `updated_at`
- `selection_fingerprint`
- `pool_build_id`
- `rank_digits`
- `limits`
- `images`

**Verboten:** Embeddings, Bildbytes, Face-Crops oder andere binaere Daten in `selection.json`.

### 5.5 Bild-Metadaten (in selection.json)

Jeder Eintrag in `images` MUSS folgende Felder enthalten:
- `source_id`
- `batch_id`
- `path` (oder `crop_source`)
- `status` (`active`, `new` oder `unknown`)
- `quality_score`
- `pool_utility_score` (oder `candidate_utility_score`)
- `pool_rank` (nur `active`)
- `approved_at` (nur `active`)

**Face-spezifisch:** `bounding_box`, `face_confidence`, `original_path`.
**Geschmack-spezifisch:** `base_score`.

`unknown` darf ausschließlich durch Recovery entstehen. Ein Eintrag mit `unknown` darf weder für Matching noch für Training verwendet werden.

### 5.6 Kapazitaetsgrenzen

| Grenze | Typ | Wirkung |
|--------|-----|---------|
| `max_active` | Hard Limit | Darf nicht ueberschritten werden; weitere Aktivierungen blockiert. |
| `max_new` | Hard Limit | Darf nicht ueberschritten werden; weitere Vorschlaege blockiert. |
| `max_new_per_batch` | Hard Limit | Pro `batch_id` darf diese Grenze nicht ueberschritten werden. |
| `min_active` | Soft Limit | Wenn der Wert unterschritten wird, pausiert nur der betroffene Adapter. Sein Score wird `null`; der übrige Batch-Lauf wird fortgesetzt. Eine Reaktivierung erfolgt erst nach erfolgreichem Rebuild mit ausreichender aktiver Referenzmenge. |
| `target_active` | Ziel | Angestrebter Bereich; System meldet, wenn deutlich darunter oder darueber. |

### 5.7 Konfiguration

```yaml
reference_pools:
  common:
    max_active: 100
    min_active: 30
    target_active: 50
    max_new: 20
    max_new_per_batch: 5

  taste:
    min_quality_score: 0.70
    max_redundancy: 0.90
    base_score_pool_size: 50

  faces:
    min_quality_score: 0.70
    max_redundancy: 0.95
    crop_size: 256
    min_face_size: 128
```
### 5.8 Sinnvolle Wertebereiche

| Parameter | Sinnvoller Bereich | Empfohlener Startwert | Begrundung |
|-----------|-------------------|----------------------|------------|
| `max_active` (Face) | 30–200 | 100 | Genug Diversitaet ohne unn oetige Rechenlast. |
| `max_active` (Geschmack) | 30–200 | 100 | Aehnlich wie Face; persoenliche Praeferenzen sind komplexer. |
| `min_active` | 20–50 | 30 | Mindestqualitaet fuer Training. |
| `target_active` | 30–100 | 50 | Zielbereich des Pools. |
| `max_new` | 10–50 | 20 | Begrenzte Anzahl offener Entscheidungen. |
| `max_new_per_batch` | 3–10 | 5 | Schutz vor Batch-Fluten. |
| `crop_size` (Face) | 128–512 | 256 | Gute Balance aus Genauigkeit und Effizienz. |
| `min_quality_score` | 0.6–0.8 | 0.7 | Filtert schlechte Bilder. |
| `max_redundancy` (Face) | 0.90–0.98 | 0.95 | Face-Crops koennen aehnlicher sein. |
| `max_redundancy` (Geschmack) | 0.85–0.95 | 0.90 | Geschmackspool soll diverser sein. |

### 5.9 Auswahl neuer Vorschlaege

Die Auswahl neuer Vorschlaege folgt derselben Logik:

1. Nur menschlich bestaetigte `keep`-Bilder sind Kandidaten.
2. Kandidaten muessen `min_quality_score` erreichen.
3. Kandidaten duerfen bestehende aktive Referenzen nicht zu stark duplizieren.
4. Es wird nach Nutzen fuer den Pool sortiert.
5. Erst danach werden `max_new_per_batch` und `max_new` angewendet.
6. Nur die besten zulaessigen Kandidaten werden als `new_refs/` oder `new_faces/` gespeichert.

**Face-Crop-Erstellung:** Face-Kandidaten werden zusaetzlich als quadratischer Gesichtsausschnitt gespeichert (z. B. 256×256 Pixel). Der Crop enthaelt nur das Gesicht, kein Umfeld. Die Metadaten enthalten Bounding Box, Gesichtskonfidenz und Originalreferenz.

**Nutzenbewertung:**
- **Geschmack:** Stil, Szene, Motive, Farben, Komposition, persoenliche Relevanz.
- **Face:** Pose, Blickrichtung, Licht, Distanz, Ausschnitt, Ausdruck.

### 5.10 Rebuild und Neu-Ranking

Ein Rebuild ist zwingend, wenn sich der aktive Referenzbestand aendert:

- Ein Bild wird von `new_*` nach `reference/` verschoben.
- Ein aktives Bild wird aus `reference/` entfernt.
- Eine aktive Referenzdatei wird veraendert oder ihr Hash aendert sich.
- Die Auswahlparameter, das relevante Modell, die Vorverarbeitung oder der Auswahlfingerprint aendern sich.
- `selection.json` und der Ordnerinhalt stimmen nicht mehr ueberein.

**Was neu aufgebaut wird:**
- Face: Referenz-Embeddings fuer die bekannte Person, Auswahl- und Cache-Fingerprint.
- Geschmack: Aktiver Praeferenzindex bzw. lokales Geschmacksprofil, bei trainierbaren Adaptern auch das lokale Modell.
- Base Score: separate, konfigurierbare Basis fuer technisches Culling.

Embeddings dürfen nie persistent gespeichert werden. Referenz-Embeddings werden nur bei Änderung des aktiven Referenzpools oder nach Container-Neustart neu aufgebaut. Innerhalb eines laufenden Container-Laufs dürfen sie bis zur nächsten Pooländerung ausschließlich im RAM gehalten werden. `selection_fingerprint` und `pool_build_id` müssen zur Cache-Validierung verglichen werden

**Schritte:**
1. Anzahl aktiver Dateien zaehlen.
2. `rank_digits` berechnen.
3. Nutzenranking berechnen.
4. Temporaere Dateien erzeugen.
5. Finale Namen setzen.
6. Neue `selection.json` validieren.
7. `selection.json` atomar ersetzen.
8. `rank_digits` und `pool_build_id` schreiben.

**Nutzenbasiertes Ranking:**

- `pool_utility_score` beschreibt den marginalen Nutzen eines Bildes fuer den aktuellen Pool.
- **Rang 1 = hoechster Nutzen**.
- **Rang n = geringster Nutzen**.

Der Nutzen muss mindestens technische Mindestqualitaet, Nicht-Redundanz, Diversitaet und poolspezifische Eignung beruecksichtigen.

### 5.11 Dynamische Stellenzahl

Die Stellenzahl der Rangzahl (`rank_digits`) wird automatisch an die Anzahl aktiver Dateien angepasst:

1. Anzahl aktiver Dateien in `reference/` zaehlen.
2. `rank_digits = max(1, ceil(log10(n + 1)))` berechnen.
3. Dateinamen formatieren als `{rank_zfill}__{original_name}_{suffix}.{ext}`.

**Beispiele:**

| n | rank_digits | Beispiel |
|---|------------|----------|
| 5 | 1 | `1__...` bis `5__...` |
| 50 | 2 | `01__...` bis `50__...` |
| 500 | 3 | `001__...` bis `500__...` |
| 1500 | 4 | `0001__...` bis `1500__...` |

**Sortierung:** Dateien werden aufsteigend nach Rang angezeigt. Rang 1 ist oben, Rang n unten. Der Mensch kann die letzten Dateien als geringsten Nutzen erkennen und loeschen.

### 5.12 Atomare Umbenennung

Nach erfolgreichem Rebuild werden alle Dateien in `reference/` neu benannt:

1. Anzahl zaehlen.
2. Stellenzahl berechnen.
3. Nutzenrang aller aktiven Referenzen neu berechnen.
4. Tempor aere eindeutige Namen verwenden.
5. Finale Namen `0001__...`, `0002__...`, ... setzen.
6. Neue `selection.json` temporaer erzeugen und validieren.
7. `selection.json` atomar ersetzen.
8. `rank_digits` und `pool_build_id` schreiben.

Scheitert ein Schritt, bleibt die vorherige Poolversion aktiv; der Fehler wird in der Run-Summary gemeldet.

### 5.13 Manuelle Bedienung

| Aktion des Menschen | Systemwirkung |
|---------------------|---------------|
| Bild aus `new_*` nach `reference/` verschieben | Konsistenzpruefung, Rebuild, neues Ranking. |
| Bild aus `new_*` loeschen | Eintrag aus `selection.json` entfernen; kein Rebuild, solange `reference/` unveraendert bleibt. |
| Aktive Datei aus `reference/` loeschen | Konsistenzpruefung, Rebuild, neues Ranking. |
| `max_new` erreicht | Keine neuen Vorschlaege; Run-Summary meldet Handlungsbedarf. |
| `max_active` erreicht | Keine neue Aktivierung; Run-Summary meldet manuelles Bereinigen. |

### 5.14 Run-Summary-Meldungen

**Meldung: `max_new` erreicht**
```json
{
  "severity": "warning",
  "type": "reference_pool_new_limit_reached",
  "pool": "faces/max_mustermann",
  "message": "Die Hoechstzahl offener Vorschlaege (max_new=20) ist erreicht; es werden keine weiteren neuen Gesichter gespeichert.",
  "action": "Bitte new_faces/ pruefen: relevante Bilder nach reference/ verschieben, uebrige Bilder loeschen."
}
```

**Meldung: `max_new_per_batch` erreicht**
```json
{
  "severity": "info",
  "type": "reference_pool_batch_limit_reached",
  "pool": "samples",
  "batch_id": "2024-08-15_Geburtstag+a3f7c2e1",
  "message": "Die Hoechstzahl offener Vorschlaege pro Batch (max_new_per_batch=5) fuer Batch '2024-08-15_Geburtstag+a3f7c2e1' ist erreicht.",
  "action": "Bitte new_refs/ pruefen: relevante Bilder nach reference/ verschieben."
}
```

**Meldung: `max_active` erreicht**
```json
{
  "severity": "info",
  "type": "reference_pool_active_limit_reached",
  "pool": "faces/max_mustermann",
  "message": "Die Hoechstzahl aktiver Referenzen (max_active=100) ist erreicht; es sind keine weiteren Aktivierungen moeglich.",
  "action": "Bitte reference/ pruefen: weniger nuetzliche Bilder entfernen, um Platz fuer neue Referenzen zu schaffen."
}
```

---

## 6. Betrieb, Konfiguration, Reporting, Abnahme

### 6.1 Konfiguration

- **Schema:** YAML mit strikter Validierung; unbekannte Schluessel sind Fehler (ausser `extensions`).
- **Fingerprint:** Effektive Konfiguration wird mit SHA256-Fingerprint im Run dokumentiert.
- **Sicherheit:** Keine Geheimnisse, keine Produktionspfade in Git.
- **Config-Schluessel:** Durchgaengig snake_case.

### 6.2 Betrieb

- **Scheduler:** Container mit persistentem NAS-Mount starten; globaler Lock verhindert parallele Laeufe.
- **Fehlerisolation:** Ein defekter Batch wird quaraentaenisiert statt den ganzen Lauf zu stoppen.
- **Ressourcenverhalten:** Auf Ziel-NAS dokumentieren.
- **Not-Stop:** Bei Zeitbudget oder SIGTERM keinen neuen teuren Schritt beginnen; sicheren aktuellen Schritt abschliessen, Status `paused` atomar schreiben, kontrolliert beenden.

### 6.3 Reporting

- **Status:** Pflicht.
- **Zweck:** Macht jedem Lauf auf einen Blick klar, was passiert ist und was der Mensch tun muss.
- **Ablauf:** JSON-Run-Summary, Scheduler-Ausgabe, CSV, Logs, `user_actions_required`.

### 6.4 Abnahme

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

---

## 7. Stil- und Formatvereinheitlichung

- Ueberschriften als Markdown-Header.
- Listen mit Bindestrichen.
- Tabellen mit Header und Trennlinie.
- Codebloecke mit Sprachangabe.
- Zitate mit `>`.

---

## 8. Wichtige Regeln

1. Git enthaelt nie Modellgewichte, private Bilder, Referenzen, Face-Crops, Embeddings, Laufzeitdaten, Caches, Logs oder Secrets.
2. NAS enthaelt alle Workflow-Daten und Konfiguration mit Produktionspfaden.
3. Docker-Container enthaelt nur Code und mountet NAS-Pfade.

---

### Anhang A — Skript-Anforderungen

#### A1 – Geltungsbereich

Diese Anforderung gilt fuer alle Skript-Dateien im Repository.

#### A2 – Struktur-Anforderungen

Jede Skript-Datei MUSS eine feste Struktur haben:

1. Header-Kommentar (6–10 Zeilen).
2. Abschnitts-Kommentare (2–3 Zeilen pro Abschnitt).
3. Funktions-Kommentare (3–5 Zeilen pro Funktion).
4. Einzeiler-Kommentare fuer komplexe Bedingungen.

#### A3 – Kommentar-Dichte und Lesbarkeit

- Header: 6–10 Zeilen.
- Jede Funktion: 3–5 Zeilen Kommentar.
- Jeder Abschnitt: 2–3 Zeilen Kommentar.
- Ca. 20 % Kommentare im Skript.
- Sprechende Namen, konsistente Formatierung, max. 80–100 Zeichen pro Zeile.

#### A4 – Beispiel-Header

```bash
#!/bin/bash
#
# Skript: scripts/run-phase1.sh
# Zweck: Fuehrt Phase 1 fuer einen Batch aus (Inventar, Culling, Metadaten)
# Autor: MaiTaiMa
# Erstellt: 2026-08-04
# Version: 1.0
# Requires: bash, docker, exiftool
# Usage: ./run-phase1.sh <batch-id>
#
# Aenderungsprotokoll:
#   2026-08-04 | v1.0 | Initiale Version
#
```

#### A5 – Beispiel-Abschnitt

```bash
# === Validierung: Pflichtargumente pruefen ===
# Zweck: Stellt sicher, dass alle erforderlichen Argumente uebergeben wurden
# Eingabe: $1 (BATCH_ID)
# Ausgabe: Fehlermeldung bei fehlendem Argument, Abbruch mit Exit-Code 1
if [ -z "$BATCH_ID" ]; then
    echo "Fehler: BATCH_ID ist erforderlich"
    echo "Usage: ./run-phase1.sh <batch-id>"
    exit 1
fi
```

#### A6 – Beispiel-Betriebsfunktion

```bash
# === Betriebsprüfung und CLI-Start ===
# Zweck: Prüft NAS-Mount und startet ausschließlich die Python-CLI.
# Fachlogik für Dateien, Scores, Manifeste und Archive liegt in Python.
mountpoint -q "$WORKFLOW_BASEDIR" || {
    echo "Fehler: NAS-Mount fehlt"
    exit 2
}

docker compose run --rm workflow \\
    python -m app.cli phase1 \\
    --config /config/config.yaml \\
    --batch-id "$BATCH_ID"
```

#### A7 – Validierung und Abnahme

- Header-Kommentar vorhanden?
- Abschnitts-Kommentare vorhanden?
- Funktions-Kommentare vorhanden?
- Ca. 20 % Kommentare?
- Sprechende Namen?
- Konsistente Formatierung?

Bei Fehlern: Skript ungueltig markieren, loggen, manuelle Korrektur.

#### A8 – Versionierung und Aenderungshistorie

- Jede Skript-Datei braucht Versionsnummer im Header.
- Jede Aenderung muss im Header dokumentiert werden.
- Jede Aenderung muss zusaetzlich im CHANGELOG.md dokumentiert werden.

---

### Anhang B — Config-Anforderungen

#### B1 – Geltungsbereich

Diese Anforderung gilt fuer alle Config-Dateien im Repository (`config.yaml` sowie erklaerte Varianten wie `config.explained.yaml`).

#### B2 – Struktur-Anforderungen

Jede Config-Datei MUSS eine feste Struktur haben:

1. Projekt-Header (4–6 Zeilen, einmalig am Dateianfang).
2. Logikblock-Kommentare vor jedem Funktionsblock (3–6 Zeilen, mit Trennlinien).
3. Variablen-Kommentare (3 Zeilen pro Variable: Zweck, Moegliche Werte, Auswirkung).
4. Zusatzzeilen fuer komplexe Variablen (`Voraussetzung:`, `Hinweis:`).

#### B3 – Kommentar-Dichte und Lesbarkeit

- Projekt-Header: 4–6 Zeilen.
- Jeder Funktionsblock: 3–6 Zeilen Logikblock-Kommentar.
- Jede Variable: 3 Zeilen Kommentar (Zweck, Werte, Auswirkung).
- Jede Variable muss vollstaendig erklaert sein, keine unkommentierten Werte.
- Sprechende Schluesselnamen, konsistente Einrueckung, max. 80–100 Zeichen pro Zeile.

#### B4 – Beispiel-Header

```yaml
# Projekt: Synology Photo Workflow
# Datei: config/config.explained.yaml
# Funktion: Erweiterte Erlaeuterung der aktuellen config.yaml mit denselben Werten.
# Hinweis: Diese Datei erklaert jede Variable explizit und beschreibt moegliche Werte und Auswirkungen.
```

#### B5 – Beispiel-Logikblock

```yaml
# -----------------------------------------------------------------------------
# phase2
# Dieser Block steuert die Sicherheitsgrenze zwischen Archivierung und Loeschung.
# Aenderungen hier sind besonders sensibel, weil sie den Umgang mit ARW-Dateien beeinflussen.
# -----------------------------------------------------------------------------
phase2:
```

#### B6 – Beispiel-Variable

```yaml
# delete_unneeded_arws_after_verified_archive: ARWs erst nach verifiziertem Archiv loeschen.
# Moegliche Werte: true oder false.
# Auswirkung: true erlaubt die kontrollierte Bereinigung nach erfolgreicher Pruefung; false loest nichts aus.
delete_unneeded_arws_after_verified_archive: true
```

Regeln fuer Variablen-Kommentare:

- Zeile 1: `<schluessel>: <eine Zeile Zweckbeschreibung>`.
- Zeile 2: `Moegliche Werte:` — vollstaendige Aufzaehlung aller erlaubten Eingaben (Enum-Werte, Wertebereiche wie `0.0 bis 1.0`, Typen wie `positive Ganzzahl` oder `null oder numerische Schwelle`, Pfadformen).
- Zeile 3: `Auswirkung:` — was der Wert konkret ausloest oder verhindert.
- Booleans: `true` aktiviert/setzt die beschriebene Funktion und loest deren Wirkung aus; `false` ist der neutrale Zustand und loest nichts aus. Die Auswirkungszeile formuliert dies explizit.
- Verschachtelte Bloecke (z. B. `taste_model`, `backends`) folgen demselben Schema: Block-Kommentar vor dem Mapping, Variablen-Kommentare je Eintrag.
- Reine Wertelisten (Prompts, Rating-Baender) erhalten einen einleitenden Kommentar statt Einzelkommentaren pro Eintrag.

#### B7 – Validierung und Abnahme

- Projekt-Header vorhanden?
- Logikblock vor jedem Funktionsblock vorhanden?
- Variablen-Kommentare mit Zweck, Werten und Auswirkung vorhanden?
- Alle moeglichen Eingabewerte vollstaendig dokumentiert?
- Boolean-Semantik (true = aktiv, false = neutral) eingehalten?
- Konsistente Formatierung und Einrueckung?

Bei Fehlern: Config ungueltig markieren, loggen, manuelle Korrektur.

#### B8 – Versionierung und Aenderungshistorie

- Jede Config-Datei braucht Versionsnummer im Header.
- Jede Aenderung muss im Header dokumentiert werden.
- Jede Aenderung muss zusaetzlich im CHANGELOG.md dokumentiert werden.


---

### Anhang C — README-Anforderungen fuer Ordner

#### C1 Geltungsbereich

Gilt fuer alle README-Dateien im NAS-Workflow-Bereich:

- `PHOTO_WORKFLOW/README.md`
- `01_TEMP_SD/README.md`
- `02_TEMP_IMAGES/README.md`
- `03_TEMP_DONE/README.md`
- `04_TEMP_FINAL/README.md`
- `00_TEMP_ERROR/README.md`
- `MANUAL_KEEP/README.md`, `MANUAL_KEEP/inbox/README.md`, `MANUAL_KEEP/used/README.md`
- `WORKFLOW_DATA/README.md` und alle direkten Unterordner

#### C2 Pflichtfelder pro README

1. Zweck
2. Eingaben
3. Prozess
4. Ausgaben
5. Manuelle Aktionen
6. Lebenszyklus
7. Fehlerfaelle
8. Konfiguration (optional, falls relevant)

#### C3 Format und Umfang

- Markdown, klare Ueberschriften, Aufzaehlungen mit Bindestrichen.
- Mindestens 100, maximal 500 Woerter.
- Deutsch, technisch praezise, frei von Floskeln.
- Mindestens ein konkretes Beispiel.
- Keine externen URLs.

#### C4 Validierung

- Alle 8 Pflichtfelder vorhanden?
- Wortumfang eingehalten?
- Ein Beispiel enthalten?
- Keine externen URLs?
- Technische Korrektheit?

#### C5 Versionierung

- README braucht Versionsnummer im Header.
- Aenderungshistorie im CHANGELOG.md.
- Migration bei Struktur- oder Prozessaenderung.

#### C6 — Beispiel-README fuer TEMP_SD

```markdown
## TEMP_SD

### Zweck
Eingang fuer neue Kameraordner. Hier werden frische DCIM-Ordner (z. B. `100CANON`) abgelegt, bevor Phase 1 beginnt.

### Eingaben
- Nur frische Kameraordner
- Nur JPGs und ARWs im Originalzustand
- Abgelegt durch Mensch oder automatischen Import

### Prozess
Phase 1 liest von hier, normalisiert Datum, lagert ARWs aus, erzeugt Batch-Struktur und bewertet JPGs.

### Ausgaben
- Nach Phase 1: Batch wird nach `TEMP_IMAGES/` ueberfuehrt.

### Manuelle Aktionen
- Neue Kameraordner ablegen (erlaubt)
- Bestehende Batches veraendern (verboten)
- Dateien loeschen (verboten)

### Lebenszyklus
Ein Batch gilt als abgeschlossen, wenn Phase 1 erfolgreich nach `TEMP_IMAGES/` verschoben wurde.

### Fehlerfaelle
- Ungueltiger Ordnername: Ignorieren, Log-Eintrag, manuelle Pruefung erforderlich.
- Fehlende ARWs: Der Batch wird nicht automatisch als Metadatenfehler behandelt. Die Zuordnung wird geprüft; bei widersprüchlicher Struktur greift `review_state_invalid`.
- Beschädigte JPGs: Phase 1 setzt `analysis_error`; der Batch oder das betroffene Artefakt wird nach dem Fehlervertrag behandelt.

### Konfiguration
- `paths.temp_sd`
- `workflow.batch_sort`
```

---

### Anhang D — Referenzpool-Vertrag

### Anhang D — Referenzpool-Feldreferenz

Die normative Referenzpool-Logik steht ausschließlich in Abschnitt 5. Dieser Anhang enthält keine zweite Regelquelle.

#### D1 – `selection.json`

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

#### D2 – Bilddatensatz

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

---

### Anhang E — Konsistenzpruefung und Recovery

#### E1 — Konsistenzpruefung

- Dateiliste lesen.
- `selection.json` lesen.
- Vergleich: jeder Eintrag muss einer Datei entsprechen; jede Datei muss einem Eintrag entsprechen.
- Fehlende Dateien aus `selection.json` entfernen.
- Neue Dateien in `selection.json` aufnehmen.

#### E2 — Recovery

- Fehlende Dateien: Eintrag aus `selection.json` entfernen und Änderung protokollieren.
- Neue nicht zuordenbare Dateien: Eintrag mit `status: unknown` aufnehmen; keine Scores vergeben; nicht für Matching oder Training verwenden; menschliche Prüfung verlangen.
- Änderung in `reference/`: Rebuild auslösen.
- Änderung in `reference/`: RAM-Embedding-Cache invalidieren.
- Änderung von Modell, Vorverarbeitung, Auswahlparametern, `selection_fingerprint` oder `pool_build_id`: Rebuild und Cache-Neuaufbau auslösen.
- Scheitert ein Rebuild: vorherige Poolversion aktiv lassen und Fehler in der Run-Summary melden.

---
