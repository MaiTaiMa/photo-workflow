# 9. Synology-Photos-API-Integration

- **Status:** Optional, capability-gesteuert und nur nach erfolgreichem Ziel-NAS-Pilotlauf aktivierbar.
- **Zweck:** PHASE3 kann die aus dem Photo Workflow stammenden, bereits lokal validierten Metadaten nach erfolgreicher Veroeffentlichung in Synology Photos abbilden. Vorrang hat die Uebertragung eines eindeutigen Treffers fuer eine **bekannte Person**. Rating, kontrollierte Tags und optional eine Beschreibung sind nachgelagert.

> **Verbindliche Realitaetsgrenze:** Synology Photos bietet in der Anwendung Personenalben, Gesichtserkennung, manuelles Taggen von Personen sowie das Bearbeiten von Ratings, Tags und Beschreibungen. Eine stabile, vollstaendig offiziell dokumentierte Public-API samt dauerhaftem Python-SDK fuer die externe Zuweisung eines Gesichtes zu einer Synology-Person ist jedoch nicht nachgewiesen. Inoffizielle, reverse-engineerte `SYNO.Foto.*`-Web-APIs enthalten eine Personen-Komponente, ihre Endpunkte, Schreibparameter, Rechte und Stabilitaet sind aber nicht garantiert. Deshalb ist keine konkrete schreibende Personen- oder Metadatenmethode Teil dieses Vertrags.

Die Personenuebertragung ist ein vorrangiges Ziel, aber keine harte Funktionszusage. Sie darf nur fuer eine bereits in Synology Photos bestehende Person erfolgen, wenn sie auf dem konkreten Ziel-NAS vollstaendig nachgewiesen, rueckgelesen und im Pilotbetrieb freigegeben wurde. Ist dies nicht moeglich, bleibt die lokale Gesichtserkennung die fachliche Quelle. Synology Photos erhaelt dann hoechstens den kontrollierten Tag `person:<slug>` als Suchhilfe.

## 9.1 Geltungsbereich und Schutzgrenzen

Die Integration ist vollstaendig nachgelagert zu PHASE1 und PHASE2. Sie darf nur fuer Batches mit dem validen Zustand `phase2_completed` starten. Dateioperationen, Transfer, Hashpruefung, Resume und PHASE3-Zustaende bleiben Aufgabe von PHASE3; der API-Adapter darf keine Dateien verschieben, kopieren, umbenennen, hochladen oder loeschen.

Der Adapter darf ausschliesslich bereits lokal vorhandene und freigegebene Werte abbilden:

1. einen eindeutigen Match einer bekannten Person aus Abschnitt 4.5;
2. das bereits bestimmte Sternrating aus Abschnitt 4.7;
3. die bereits eingebetteten und rueckgelesenen Workflow-Tags aus Abschnitt 4.7;
4. eine optional explizit freigegebene Beschreibung.

Der Adapter darf **nicht**:

- unbekannte Gesichter, unbekannte Personen, Face-Crops, Embeddings oder Referenzbilder uebertragen, speichern, taggen oder zuordnen;
- eine Person in Synology Photos automatisch erzeugen, zusammenfuehren, umbenennen oder loeschen;
- Scores, Serien, Entscheidungen, Kalibrierungsdaten oder Referenzpools neu berechnen oder veraendern;
- Bildbytes, Vorschaubilder, lokale Pfade, Hashes, Archive, Manifeste, Caches oder Fehlerursachen uebertragen;
- nicht dokumentierte Endpunkte durch Raten, UI-Automatisierung oder Modifikation des Synology-Photos-Pakets erzwingen.

Ein API-Fehler oder eine nicht vorhandene Personen-Schreibfaehigkeit darf PHASE2 nie zuruecksetzen und darf keine Dateioperation ausloesen.

## 9.2 Konsistenz zu Face-Erkennung und Bewertung

### 9.2.1 Bekannte Personen

Die Synology-Integration darf nur die Ergebnisse der lokalen bekannten Gesichtserkennung verwenden. Ein uebertragbarer Personenmatch liegt nur vor, wenn alle folgenden Bedingungen erfuellt sind:

- Der lokale Face-Adapter ist aktiviert.
- Der Vergleich erfolgte gegen aktive Referenzen unter `WORKFLOW_DATA/faces/<slug>/reference` mit gueltiger `selection.json` und Status `active`.
- Der Treffer ist gegenueber dem zweitbesten Treffer eindeutig und erfuellt konfigurierte Schwelle und Sicherheitsmarge.
- Der lokale `family_score` ist gesetzt; ein `None`-Wert, ein Analysefehler oder ein unbekanntes Gesicht ist nicht uebertragbar.
- Die Person ist durch den menschlich gepflegten `slug` bereits lokal bekannt.

`family_score` bleibt ein moderates positives Culling-Signal. Er darf technische Mindestqualitaet, `manual_keep`, eine menschliche Endentscheidung, Serienlogik oder Schutzregeln niemals ueberstimmen. Die API uebernimmt nur das abschliessende, lokal vorhandene Ergebnis; sie berechnet keinen `family_score` und beeinflusst keine Bewertung.

### 9.2.2 Face-Crops, Embeddings und Referenzen

Automatisch erzeugte Face-Crops duerfen ausschliesslich lokal unter `WORKFLOW_DATA/faces/<slug>/new_faces/` liegen. Ihre manuelle Aktivierung nach `reference/` bleibt der einzige Aktivierungsschritt. Der Adapter darf weder Face-Crops noch Referenzbilder, Bounding-Box-Pixelwerte oder Embeddings persistent in API-Artefakten ablegen oder an Synology Photos uebertragen.

Eine Bounding Box darf nur fluechtig im RAM an eine auf dem Ziel-NAS nachgewiesene Personen-Zuordnung uebergeben werden. Ist dies nicht moeglich, wird keine Personen-Zuordnung geschrieben.

### 9.2.3 Rating und finale Entscheidung

Das Rating wird lokal aus dem bereits bestimmten Score-Band erzeugt und gemaess Abschnitt 4.7 per `exiftool` geschrieben sowie rueckgelesen. Der API-Adapter darf nur dieses rueckgelesene lokale Rating von 0 bis 5 unveraendert abbilden.

Ein lokales `analysis_error`, `failed_metadata`, ein nicht rueckgelesenes Rating oder eine nicht finale Entscheidung blockiert die betreffende API-Metadatenoperation. Der Adapter darf keinen Ersatzwert schreiben.

## 9.3 Konsistenz zu Workflow-Tags

Die API darf nur den folgenden, in Abschnitt 4.7 definierten und lokal vorhandenen Tagsatz verwenden:

| Lokale Quelle | API-Ziel | Regel |
|---|---|---|
| `workflow:ai_cull` | Allgemeiner Tag | Nur bei lokalem Ruecklese-Erfolg. |
| `decision:final` | Allgemeiner Tag | Nur fuer die bereits lokal bestimmte finale Entscheidung. |
| `series:*` | Allgemeiner Tag | Nur vorhandene Serieninformationen. |
| `family:match` | Allgemeiner Tag | Nur bei eindeutigem bekannten Personenmatch. |
| `person:<slug>` | Allgemeiner Tag oder nachgewiesene Personen-Zuordnung | Tag ist immer nur eine Suchhilfe; eine echte Personen-Zuordnung erfordert das Personen-Capability-Gate. |
| `manual_keep:true` | Allgemeiner Tag | Nur bei bestaetigtem Manual-Keep-Match. |

Der Adapter darf keine neuen Tags erfinden, bestehende Fremd-Tags loeschen oder aus einem Tag eine Personen-Identitaet ableiten. `person:<slug>` ist kein Ersatz fuer eine verifizierte Synology-Personenzuordnung und darf nicht als deren Erfolg protokolliert werden.

## 9.4 Tatsaechliche Synology-Photos-Grenzen

Synology Photos kann Gesichter in People-Alben gruppieren; die Anwendung erlaubt das Benennen, Zusammenfuehren, Entfernen, Neu-Zuweisen und manuelle Taggen von Personen. Diese Bedienfunktionen beweisen jedoch nicht, dass eine gleichwertige, stabile und oeffentlich dokumentierte API fuer externe Personen-Zuordnungen zur Verfuegung steht.

Inoffizielle Dokumentation nennt `SYNO.Foto.Browse.Person` und Methoden wie `get`, `list`, `list_face`, `set`, `merge` und `separate`. Die erforderlichen Schreibparameter, die Bindung einer Face-Bounding-Box an ein Foto sowie ihr Versions- und Berechtigungsverhalten sind dort nicht als stabiler, offizieller Vertrag nachgewiesen. Diese Informationen duerfen daher nur fuer Discovery und einen isolierten Pilotversuch verwendet werden.

Die alte Python-API fuer **Photo Station** ist kein Adapter fuer **Synology Photos** und darf nicht verwendet werden. Eine allgemeine Python-Bibliothek, die DSM- oder Photos-APIs auflistet, ersetzt ebenfalls keinen erfolgreichen Schreibtest auf dem Ziel-NAS.

## 9.5 Voraussetzungen

Die API-Integration darf nur aktiviert werden, wenn alle folgenden Bedingungen erfuellt sind:

1. Der Batch besitzt den Zustand `phase2_completed`.
2. `finalization.enabled: true` und `publish_to_synology_photos.enabled: true` sind gesetzt.
3. Der Batch wurde nach `target_folder` vollstaendig uebertragen und per Dateiliste, Groesse und SHA256 validiert.
4. `target_folder` liegt innerhalb von `paths.publish_root`, ist lokal auf dem NAS und wird im konfigurierten Synology-Photos-Space indexiert.
5. `synology_api.enabled: true` ist gesetzt.
6. Alle API-Credentials und Session-Token werden ausschliesslich als Container-Umgebungsvariablen bereitgestellt.
7. Der Adapter hat auf dem konkreten Ziel-NAS Authentisierung, Space-Zugriff, eindeutige Item-Aufloesung, erlaubte Metadatenoperationen und gegebenenfalls die Personen-Zuordnung erfolgreich geprueft.

Fehlt eine Voraussetzung, darf der Adapter keine schreibende Operation ausfuehren.

## 9.6 Konfiguration

Die zentrale `config.yaml` bleibt secrets-frei.

```yaml
finalization:
  enabled: false

  publish_to_synology_photos:
    enabled: false
    mode: copy
    target_folder: /volume1/photo/Workflow
    wait_for_index_seconds: 30
    max_index_wait_seconds: 900

  synology_api:
    enabled: false
    adapter: synology_photos_webapi
    space: shared
    timeout_seconds: 10
    retry_count: 3
    retry_backoff_seconds: 3
    dry_run: true
    require_readback: true

    write_known_persons: false
    write_rating: true
    write_tags: true
    write_description: false
```

**Konfigurationsvertrag:**

- Alle Veroeffentlichungs- und API-Optionen sind standardmaessig `false`.
- `synology_api.enabled: true` ist nur gueltig, wenn `finalization.enabled` und `publish_to_synology_photos.enabled` ebenfalls `true` sind.
- `space` muss `shared` oder `personal` sein; andere Werte sind Konfigurationsfehler.
- `dry_run: true` darf weder Transfer noch API-Schreiboperationen ausfuehren.
- `write_known_persons: true` ist nur gueltig, wenn ein erfolgreicher und dokumentierter Personen-Pilotlauf fuer denselben NAS-, DSM-, Synology-Photos- und Space-Stand vorliegt.
- Bei `write_known_persons: false` darf der Adapter keine Personen-API aufrufen; `person:<slug>` kann weiterhin als erlaubter Tag geschrieben werden.
- `require_readback: true` ist fuer Personen-Zuordnung, Rating und Tags verpflichtend.

## 9.7 Adapter- und Capability-Vertrag

Die Synology-spezifische Kommunikation liegt ausschliesslich in einem Adapter, beispielsweise `app/synology_photos_adapter.py`. Transfer, Dateioperationen, PHASE3-State, Hashpruefungen und Recovery bleiben ausserhalb des Adapters.

```python
class SynologyPhotosAdapterProtocol:
    def healthcheck(self) -> ApiCapabilityReport: ...
    def resolve_item(self, relative_path: str, space: str) -> ResolvedPhotoItem: ...
    def get_metadata(self, item_id: str) -> PublishedMetadata: ...
    def resolve_existing_person(self, slug: str, space: str) -> ResolvedPerson: ...
    def assign_existing_person(
        self,
        item_id: str,
        person_id: str,
        bounding_box: NormalizedBoundingBox,
    ) -> ApiWriteResult: ...
    def set_rating(self, item_id: str, rating: int) -> ApiWriteResult: ...
    def ensure_tags(self, item_id: str, tags: list[str]) -> ApiWriteResult: ...
    def set_description(self, item_id: str, description: str) -> ApiWriteResult: ...
```

Diese Schnittstelle ist ein lokaler Vertrag, keine Behauptung bestimmter Synology-Endpunkte. `assign_existing_person` darf nur implementiert und aufgerufen werden, wenn sie im Ziel-NAS-Pilotlauf als sicher, idempotent und ruecklesbar nachgewiesen wurde.

Vor jedem produktiven Lauf muss `healthcheck()` einen secrets-freien `ApiCapabilityReport` erzeugen. Er muss mindestens pruefen:

- API-Discovery und erfolgreiche Authentisierung;
- Erreichbarkeit des konfigurierten Personal- oder Shared-Space;
- eindeutige Aufloesung eines publizierten Testbilds;
- Lese- und Schreibfaehigkeit fuer jede aktivierte Metadatenart;
- bei `write_known_persons: true`: Aufloesung einer bestehenden Testperson, Personen-Zuordnung zu einem Testbild und erfolgreiche Ruecklesepruefung.

Nicht nachgewiesene Faehigkeiten gelten als `capability_unsupported`. Sie duerfen nicht durch vermutete private Endpunkte erzwungen werden.

## 9.8 Sichere Item- und Personen-Aufloesung

Ein Zielbild darf nicht allein anhand seines Dateinamens gefunden werden. Die Aufloesung erfolgt in dieser Reihenfolge:

1. Serverseitiger Pfad oder gleichwertige eindeutige Referenz.
2. Exakter relativer Pfad unter dem veroeffentlichten Batch-Zielpfad.
3. Dateiname **und** aufgeloester Batch-Zielordner.
4. Weitere vom Ziel-NAS nachweislich bereitgestellte eindeutige Dateieigenschaft.

Die Zuordnung `person_slug` zu einer bestehenden Synology-Person muss im Pilotlauf bewusst und eindeutig angelegt werden. Ein sichtbarer Name allein reicht nicht. Mehrdeutige Items oder Personen fuehren zu `item_ambiguous` beziehungsweise `person_ambiguous`; es darf keine Personen-Zuordnung geschrieben werden.

Die Personen-Zuordnung erfordert eine zum Zielbild validierbare, normalisierte Bounding Box. Rotation, Zuschnitt, Neucodierung oder abweichende Bilddimensionen, die eine eindeutige Geometrie verhindern, setzen `geometry_validation_failed`. Der Adapter darf dann nur den erlaubten `person:<slug>`-Tag als Fallback schreiben, sofern Tags aktiviert und nachweislich schreibbar sind.

## 9.9 Ablauf, Idempotenz und Ruecklesepruefung

1. PHASE3 validiert State, Konfiguration, Pfade und `finalization_manifest.json`.
2. Nach erfolgreichem Transfer wird mindestens `wait_for_index_seconds` auf die Indexierung gewartet.
3. Bis `max_index_wait_seconds` wird die eindeutige Item-Aufloesung wiederholt. Danach wird `phase3_indexing_timeout` gesetzt; es erfolgt keine Dateiaktion.
4. Der Adapter erstellt oder aktualisiert den Capability-Report.
5. Fuer jedes eindeutig aufgeloeste Item validiert der Adapter zuerst die lokale Endentscheidung, das Rating und die lokal rueckgelesenen Tags.
6. Bei aktiviertem und nachgewiesenem `write_known_persons` prueft er den bekannten Face-Match, die bestehende Synology-Person und die Bildgeometrie; erst dann darf die Personen-Zuordnung erfolgen.
7. Rating, Tags und optionale Beschreibung werden nur nachgewiesen unterstuetzt und unabhaengig idempotent verarbeitet.
8. Bereits korrekte Personenverknuepfungen, Ratings, Tags und Beschreibungen sind Erfolg und werden nicht erneut geschrieben.
9. Jede als Erfolg gemeldete Operation muss bei `require_readback: true` erneut gelesen und mit dem erwarteten lokalen Payload verglichen werden.
10. Jeder API-Versuch wird atomar mit Zeitstempel, Konfigurationsfingerprint und Ergebnis protokolliert.

Ein Schreibvorgang ohne bestaetigbare Ruecklesepruefung ist `partial`, nicht `success`.

## 9.10 Lokaler Datenvertrag

Bei API-Nutzung muss pro Bild ein lokaler, secrets-freier Korrelationsrecord bestehen:

```json
{
  "relative_path": "2024-08-15_Geburtstag/IMG_0001.JPG",
  "resolved_item_status": "resolved",
  "metadata_status": "verified",
  "attempt_count": 1,
  "last_error": null
}
```

Bei aktivierter und erfolgreicher Personen-Zuordnung darf der Record zusaetzlich `person_slug` und `person_assignment_status` enthalten. Er darf keine Person-ID, Face-Crops, Embeddings, Bildbytes, Bounding-Box-Werte, Sessiondaten oder Secrets enthalten.

Der PHASE3-State muss mindestens `batch_id`, `source_batch_path`, `target_batch_path`, `publish_enabled`, `transfer_mode`, `state`, `timestamp`, `config_fingerprint`, `producer_version` und `finalization_manifest_hash` enthalten.

## 9.11 Fehler und Resume

| Fehlerklasse | Wirkung |
|---|---|
| `auth_failed` | API-Teil blockieren; Transfer und PHASE2 nicht zurueckrollen. |
| `capability_unsupported` | Betroffene Personen- oder Metadatenart ueberspringen und melden. |
| `person_not_found` | Keine Person erzeugen; als Benutzeraktion melden. |
| `person_ambiguous` | Keine Personen-Zuordnung schreiben. |
| `item_not_found` | Bis zum Index-Timeout wiederholen; kein Schreiben. |
| `item_ambiguous` | Keine API-Schreiboperation. |
| `geometry_validation_failed` | Keine Personen-Zuordnung; nur erlaubter Tag-Fallback. |
| `transient_api_error` | Begrenzt mit Backoff wiederholen. |
| `readback_mismatch` | `phase3_api_metadata_partial` setzen; spaeter fortsetzen. |

Ein API-Fehler darf niemals eine Loeschung, ein Ueberschreiben, einen Ruecktransfer oder einen automatischen Rueckwaerts-Move ausloesen. Ein bereits vollstaendig und hashgleich veroeffentlichter Batch bleibt im Zielpfad. Ein Folgejob darf nur die noch fehlende Index-, Item-, Personen- oder Metadatenpruefung fortsetzen.

## 9.12 Abnahme

Die Integration ist nur abnahmefaehig, wenn ein isolierter Pilot auf dem konkreten Ziel-NAS zeigt:

1. API-Discovery, Authentisierung und Space-Zugriff funktionieren ohne Secrets in Logs, CSVs, Manifests oder Reports.
2. Ein eindeutig bekanntes Testbild wird nach Indexierung aufgeloest.
3. Rating und alle aktivierten Workflow-Tags werden nur aus lokal rueckgelesenen Werten uebernommen und nach dem Schreiben rueckgelesen.
4. Ein `family:match`- und `person:<slug>`-Tag wird nur bei einem eindeutigen lokalen bekannten Personenmatch gesetzt.
5. Bei aktivierter Personen-Zuordnung wird eine vorab bestehende Synology-Testperson eindeutig aufgeloest, einem Testbild zugeordnet und rueckgelesen.
6. Wiederholung derselben Personen- oder Metadatenoperation ist idempotent.
7. Mehrdeutige Person, mehrdeutiges Item, unbekanntes Gesicht, fehlende Bounding Box oder ungleiche Bildgeometrie fuehren zu keiner Personen-Schreiboperation.
8. Ein absichtlich fehlschlagender API-Aufruf veraendert weder Bilddateien noch Archive noch Phase-2-Status.
9. `dry_run: true` fuehrt weder Transfer noch API-Schreiboperationen aus.

**Nicht ausreichend fuer die Abnahme:** Eine erfolgreiche DSM-Anmeldung, eine sichtbare People-Oberflaeche, die Existenz einer inoffiziellen Personen-API oder das blosse Setzen eines `person:<slug>`-Tags. Fuer `write_known_persons: true` ist die vollstaendige, zielsystemspezifische Kette aus eindeutiger Item-Aufloesung, bestehender Person, validierter Geometrie, Schreiboperation und Ruecklesepruefung erforderlich.

---

**Status:** Optional. Kann das Ziel-NAS keine sichere Personen-Zuordnung per API nachweisen, bleibt PHASE3 nach sicherem Transfer voll funktionsfaehig. Die lokale Face-Erkennung und ihre manuell gepflegten Referenzpools bleiben die fachliche Quelle; Synology Photos kann dann seine eigene Gesichtserkennung verwenden und erhaelt lediglich die kontrollierten lokalen Metadaten.